import java.io.BufferedReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.DigestInputStream;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;

import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVParser;
import org.apache.commons.csv.CSVRecord;

import com.orientechnologies.orient.core.db.ODatabaseSession;
import com.orientechnologies.orient.core.db.ODatabaseType;
import com.orientechnologies.orient.core.db.OrientDB;
import com.orientechnologies.orient.core.db.OrientDBConfig;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.metadata.schema.OClass;
import com.orientechnologies.orient.core.metadata.schema.OSchema;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.record.OElement;
import com.orientechnologies.orient.core.record.OEdge;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.OVertex;

public class OrientDbCsvLoader {
    static String requireEnvironment(String name) {
        String value = System.getenv(name);
        if (value == null || value.isEmpty()) {
            throw new IllegalStateException(name + " must be set in the process environment");
        }
        return value;
    }

    static class Column {
        final String name;
        final String type;

        Column(String name, String type) {
            this.name = name;
            this.type = type;
        }
    }

    static class Table {
        String kind;
        String name;
        String source;
        String csv;
        List<Column> columns = new ArrayList<>();
        List<Column> csvColumns = new ArrayList<>();
        Map<String, String> rename = new LinkedHashMap<>();
        String primaryKey;
        String fromCol;
        String toCol;
        String fromVertex;
        String toVertex;
        String fromPk;
        String toPk;

        boolean isVertex() {
            return "V".equals(kind);
        }

        boolean isEdge() {
            return "E".equals(kind);
        }

        boolean isPlain() {
            return "P".equals(kind);
        }
    }

    static class Args {
        Path dbRoot;
        String sf;
        Path dataDir;
        Path updateDir;
        Path configDir;
        int batchSize = 5000;
        int maxRows = 0;
        boolean rebuild = false;
        boolean skipUpdates = false;
        boolean skipSourceCount = false;
        boolean skipFinalCounts = false;
        boolean resume = false;
        boolean repairSkippedEdges = false;
        boolean deriveUpdatesOnly = false;
        String onlyClass = "";
        final Set<String> deriveClasses = new HashSet<>();
        final Set<String> resumePartialEdgePrefixes = new HashSet<>();
        String orphanEdgeMode = "skip";
        String updateSourceMode = "derived";
        String loaderConfigSha256 = "";
        final Set<String> compatibleLoaderConfigSha256s = new HashSet<>();
        final Map<String, SourceFingerprint> sourceFingerprints = new HashMap<>();
    }

    static class PendingRid {
        final String key;
        final OVertex vertex;

        PendingRid(String key, OVertex vertex) {
            this.key = key;
            this.vertex = vertex;
        }
    }

    static class SourceFingerprint {
        final long rows;
        final String sha256;

        SourceFingerprint(long rows, String sha256) {
            this.rows = rows;
            this.sha256 = sha256;
        }
    }

    static Args parseArgs(String[] argv) {
        Args args = new Args();
        for (int i = 0; i < argv.length; i++) {
            String a = argv[i];
            if ("--db-root".equals(a)) {
                args.dbRoot = Paths.get(argv[++i]);
            } else if ("--sf".equals(a)) {
                args.sf = argv[++i];
            } else if ("--data-dir".equals(a)) {
                args.dataDir = Paths.get(argv[++i]);
            } else if ("--update-dir".equals(a)) {
                args.updateDir = Paths.get(argv[++i]);
            } else if ("--config-dir".equals(a)) {
                args.configDir = Paths.get(argv[++i]);
            } else if ("--batch-size".equals(a)) {
                args.batchSize = Integer.parseInt(argv[++i]);
            } else if ("--max-rows".equals(a)) {
                args.maxRows = Integer.parseInt(argv[++i]);
            } else if ("--rebuild".equals(a)) {
                args.rebuild = true;
            } else if ("--skip-updates".equals(a)) {
                args.skipUpdates = true;
            } else if ("--skip-source-count".equals(a)) {
                args.skipSourceCount = true;
            } else if ("--skip-final-counts".equals(a)) {
                args.skipFinalCounts = true;
            } else if ("--resume".equals(a)) {
                args.resume = true;
            } else if ("--repair-skipped-edges".equals(a)) {
                args.repairSkippedEdges = true;
            } else if ("--derive-updates-only".equals(a)) {
                args.deriveUpdatesOnly = true;
            } else if ("--derive-classes".equals(a)) {
                for (String name : argv[++i].split(",")) {
                    if (!name.trim().isEmpty()) {
                        args.deriveClasses.add(name.trim());
                    }
                }
            } else if ("--resume-partial-edge-prefixes".equals(a)) {
                for (String name : argv[++i].split(",")) {
                    if (!name.trim().isEmpty()) {
                        args.resumePartialEdgePrefixes.add(name.trim());
                    }
                }
            } else if ("--compatible-loader-config-sha256s".equals(a)) {
                for (String checksum : argv[++i].split(",")) {
                    if (!checksum.trim().isEmpty()) {
                        args.compatibleLoaderConfigSha256s.add(checksum.trim());
                    }
                }
            } else if ("--only-class".equals(a)) {
                args.onlyClass = argv[++i];
            } else if ("--orphan-edge-mode".equals(a)) {
                args.orphanEdgeMode = argv[++i];
            } else if ("--update-source-mode".equals(a)) {
                args.updateSourceMode = argv[++i];
            } else {
                throw new IllegalArgumentException("unknown argument: " + a);
            }
        }
        if (args.dbRoot == null || args.sf == null || args.dataDir == null || args.updateDir == null || args.configDir == null) {
            throw new IllegalArgumentException("missing required argument");
        }
        if (!"skip".equals(args.orphanEdgeMode) && !"placeholder".equals(args.orphanEdgeMode)) {
            throw new IllegalArgumentException("--orphan-edge-mode must be skip or placeholder");
        }
        if (!"csv".equals(args.updateSourceMode) && !"derived".equals(args.updateSourceMode)) {
            throw new IllegalArgumentException("--update-source-mode must be csv or derived");
        }
        if (args.deriveUpdatesOnly && !"derived".equals(args.updateSourceMode)) {
            throw new IllegalArgumentException("--derive-updates-only requires --update-source-mode derived");
        }
        if (!args.resumePartialEdgePrefixes.isEmpty() && !args.resume) {
            throw new IllegalArgumentException("--resume-partial-edge-prefixes requires --resume");
        }
        if (!args.resumePartialEdgePrefixes.isEmpty() && args.maxRows > 0) {
            throw new IllegalArgumentException("prefix edge resume cannot be combined with --max-rows");
        }
        return args;
    }

    static List<Column> parseColumns(String text) {
        List<Column> cols = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return cols;
        }
        for (String part : text.split(";")) {
            if (part.isEmpty()) {
                continue;
            }
            String[] pieces = part.split(":", 2);
            cols.add(new Column(pieces[0], pieces.length > 1 ? pieces[1] : "STRING"));
        }
        return cols;
    }

    static Map<String, String> parseRename(String text) {
        Map<String, String> rename = new LinkedHashMap<>();
        if (text == null || text.isEmpty()) {
            return rename;
        }
        for (String part : text.split(";")) {
            String[] pieces = part.split(">", 2);
            if (pieces.length == 2) {
                rename.put(pieces[0], pieces[1]);
            }
        }
        return rename;
    }

    static List<Table> readTables(Path configDir) throws IOException {
        List<Table> tables = new ArrayList<>();
        try (BufferedReader br = Files.newBufferedReader(configDir.resolve("tables.tsv"), StandardCharsets.UTF_8)) {
            String header = br.readLine();
            if (header == null) {
                throw new IOException("empty tables.tsv");
            }
            String line;
            while ((line = br.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                String[] p = line.split("\t", -1);
                Table t = new Table();
                t.kind = p[0];
                t.name = p[1];
                t.source = p[2];
                t.csv = p[3];
                t.columns = parseColumns(p[4]);
                t.csvColumns = parseColumns(p[5]);
                t.rename = parseRename(p[6]);
                t.primaryKey = p[7];
                t.fromCol = p[8];
                t.toCol = p[9];
                t.fromVertex = p[10];
                t.toVertex = p[11];
                t.fromPk = p[12];
                t.toPk = p[13];
                tables.add(t);
            }
        }
        return tables;
    }

    static Map<String, Set<String>> readIndexes(Path configDir) throws IOException {
        Map<String, Set<String>> indexes = new LinkedHashMap<>();
        Path path = configDir.resolve("indexes.tsv");
        if (!Files.exists(path)) {
            return indexes;
        }
        try (BufferedReader br = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
            br.readLine();
            String line;
            while ((line = br.readLine()) != null) {
                if (line.trim().isEmpty()) {
                    continue;
                }
                String[] p = line.split("\t", -1);
                Set<String> cols = new HashSet<>();
                if (p.length > 1 && !p[1].isEmpty()) {
                    for (String col : p[1].split(";")) {
                        if (!col.isEmpty()) {
                            cols.add(col);
                        }
                    }
                }
                indexes.put(p[0], cols);
            }
        }
        return indexes;
    }

    static OType otype(String type) {
        String t = type.toUpperCase();
        if ("LONG".equals(t) || "BIGINT".equals(t) || "INTEGER".equals(t) || "INT".equals(t)) {
            return OType.LONG;
        }
        if ("DOUBLE".equals(t) || "FLOAT".equals(t) || "REAL".equals(t)) {
            return OType.DOUBLE;
        }
        return OType.STRING;
    }

    static Object parseValue(String raw, String type) {
        if (raw == null) {
            return null;
        }
        String v = raw.trim();
        if (v.isEmpty()) {
            return null;
        }
        String t = type.toUpperCase();
        try {
            if ("LONG".equals(t) || "BIGINT".equals(t) || "INTEGER".equals(t) || "INT".equals(t)) {
                return Long.parseLong(v);
            }
            if ("DOUBLE".equals(t) || "FLOAT".equals(t) || "REAL".equals(t)) {
                return Double.parseDouble(v);
            }
        } catch (NumberFormatException ignored) {
            return null;
        }
        return raw;
    }

    static String originFor(Table table, String outputColumn) {
        for (Map.Entry<String, String> e : table.rename.entrySet()) {
            if (e.getValue().equals(outputColumn)) {
                return e.getKey();
            }
        }
        return outputColumn;
    }

    static Path sourcePath(Args args, Table table) {
        return ("UPDATE".equals(table.source) ? args.updateDir : args.dataDir).resolve(table.csv);
    }

    static Table findTable(List<Table> tables, String name) {
        for (Table table : tables) {
            if (table.name.equals(name)) {
                return table;
            }
        }
        return null;
    }

    static boolean shouldVisitVertexForOnlyClass(Args args, List<Table> tables, Table vertex) {
        if (args.onlyClass.isEmpty() || args.onlyClass.equals(vertex.name)) {
            return true;
        }
        Table target = findTable(tables, args.onlyClass);
        if (target == null || !target.isEdge()) {
            return false;
        }
        return vertex.name.equals(target.fromVertex) || vertex.name.equals(target.toVertex);
    }

    static void createSchema(ODatabaseSession db, List<Table> tables) {
        OSchema schema = db.getMetadata().getSchema();
        if (!schema.existsClass("_LoadManifest")) {
            OClass manifest = schema.createClass("_LoadManifest", 1);
            manifest.createProperty("class_name", OType.STRING);
            manifest.createProperty("source_rows", OType.LONG);
            manifest.createProperty("loaded_rows", OType.LONG);
            manifest.createProperty("skipped_rows", OType.LONG);
            manifest.createProperty("placeholder_rows", OType.LONG);
            manifest.createProperty("orphan_edge_mode", OType.STRING);
            manifest.createProperty("loader_mode", OType.STRING);
            manifest.createProperty("status", OType.STRING);
            manifest.createProperty("updated_at", OType.STRING);
            manifest.createProperty("source_kind", OType.STRING);
            manifest.createProperty("source_file", OType.STRING);
            manifest.createProperty("source_sha256", OType.STRING);
            manifest.createProperty("source_rows_verified", OType.BOOLEAN);
            manifest.createProperty("loader_config_sha256", OType.STRING);
            manifest.createProperty("resume_mode", OType.STRING);
            manifest.createProperty("resume_prefix_rows", OType.LONG);
            manifest.createProperty("resume_prefix_assumption", OType.STRING);
        } else {
            OClass manifest = schema.getClass("_LoadManifest");
            if (!manifest.existsProperty("skipped_rows")) {
                manifest.createProperty("skipped_rows", OType.LONG);
            }
            if (!manifest.existsProperty("loader_mode")) {
                manifest.createProperty("loader_mode", OType.STRING);
            }
            if (!manifest.existsProperty("placeholder_rows")) {
                manifest.createProperty("placeholder_rows", OType.LONG);
            }
            if (!manifest.existsProperty("orphan_edge_mode")) {
                manifest.createProperty("orphan_edge_mode", OType.STRING);
            }
            if (!manifest.existsProperty("source_kind")) {
                manifest.createProperty("source_kind", OType.STRING);
            }
            if (!manifest.existsProperty("source_file")) {
                manifest.createProperty("source_file", OType.STRING);
            }
            if (!manifest.existsProperty("source_sha256")) {
                manifest.createProperty("source_sha256", OType.STRING);
            }
            if (!manifest.existsProperty("source_rows_verified")) {
                manifest.createProperty("source_rows_verified", OType.BOOLEAN);
            }
            if (!manifest.existsProperty("loader_config_sha256")) {
                manifest.createProperty("loader_config_sha256", OType.STRING);
            }
            if (!manifest.existsProperty("resume_mode")) {
                manifest.createProperty("resume_mode", OType.STRING);
            }
            if (!manifest.existsProperty("resume_prefix_rows")) {
                manifest.createProperty("resume_prefix_rows", OType.LONG);
            }
            if (!manifest.existsProperty("resume_prefix_assumption")) {
                manifest.createProperty("resume_prefix_assumption", OType.STRING);
            }
        }
        if (!schema.existsClass("_MissingEndpoint")) {
            OClass placeholder = schema.createClass("_MissingEndpoint", 1, schema.getClass("V"));
            placeholder.createProperty("target_class", OType.STRING);
            placeholder.createProperty("target_key", OType.STRING);
            placeholder.createProperty("target_value", OType.STRING);
        }
        for (Table table : tables) {
            OClass cls;
            if (table.isVertex()) {
                cls = schema.existsClass(table.name)
                        ? schema.getClass(table.name)
                        : schema.createClass(table.name, 1, schema.getClass("V"));
            } else if (table.isEdge()) {
                cls = schema.existsClass(table.name)
                        ? schema.getClass(table.name)
                        : schema.createClass(table.name, 1, schema.getClass("E"));
            } else {
                cls = schema.existsClass(table.name) ? schema.getClass(table.name) : schema.createClass(table.name, 1);
            }
            for (Column col : table.columns) {
                if (!cls.existsProperty(col.name)) {
                    try {
                        cls.createProperty(col.name, otype(col.type));
                    } catch (Exception ex) {
                        System.err.println("WARN create property " + table.name + "." + col.name + ": " + ex.getMessage());
                    }
                }
            }
        }
    }

    static boolean isComplete(Args args, ODatabaseSession db, Table table) {
        try {
            String sql = "SELECT source_file,source_sha256,source_rows_verified,loader_config_sha256 FROM _LoadManifest "
                    + "WHERE class_name = ? AND status = 'DONE' LIMIT 1";
            try (com.orientechnologies.orient.core.sql.executor.OResultSet rs = db.query(sql, table.name)) {
                if (rs.hasNext()) {
                    com.orientechnologies.orient.core.sql.executor.OResult row = rs.next();
                    Object sourceFile = row.getProperty("source_file");
                    Object sourceSha256 = row.getProperty("source_sha256");
                    Object rowsVerified = row.getProperty("source_rows_verified");
                    Object configSha256 = row.getProperty("loader_config_sha256");
                    Path path = sourcePath(args, table);
                    SourceFingerprint fingerprint = args.sourceFingerprints.get(
                            path.toAbsolutePath().normalize().toString());
                    String currentSourceSha256 = fingerprint == null
                            ? sha256(path)
                            : fingerprint.sha256;
                    return Boolean.TRUE.equals(rowsVerified)
                            && sourceFile != null
                            && sourceSha256 != null
                            && configSha256 != null
                            && args.compatibleLoaderConfigSha256s.contains(configSha256.toString())
                            && path.toAbsolutePath().normalize().toString().equals(sourceFile.toString())
                            && currentSourceSha256.equals(sourceSha256.toString());
                }
            }
        } catch (Exception ex) {
        }
        return false;
    }

    static void markComplete(
            ODatabaseSession db,
            Table table,
            long sourceRows,
            long loadedRows,
            long skippedRows,
            long placeholderRows,
            String orphanEdgeMode,
            String sourceKind,
            String sourceFile,
            String sourceSha256,
            boolean sourceRowsVerified,
            String loaderConfigSha256) {
        try {
            db.command("DELETE FROM _LoadManifest WHERE class_name = ?", table.name).close();
            OElement doc = db.newElement("_LoadManifest");
            doc.setProperty("class_name", table.name);
            doc.setProperty("source_rows", sourceRows);
            doc.setProperty("loaded_rows", loadedRows);
            doc.setProperty("skipped_rows", skippedRows);
            doc.setProperty("placeholder_rows", placeholderRows);
            doc.setProperty("orphan_edge_mode", orphanEdgeMode);
            doc.setProperty(
                    "loader_mode",
                    "placeholder".equals(orphanEdgeMode)
                            ? "workload_projection_native_graph_placeholder_orphans"
                            : "workload_projection_native_graph");
            doc.setProperty("status", "DONE");
            doc.setProperty("updated_at", java.time.Instant.now().toString());
            doc.setProperty("source_kind", sourceKind);
            doc.setProperty("source_file", sourceFile);
            doc.setProperty("source_sha256", sourceSha256);
            doc.setProperty("source_rows_verified", sourceRowsVerified);
            doc.setProperty("loader_config_sha256", loaderConfigSha256);
            doc.save();
        } catch (Exception ex) {
            System.err.println("WARN mark complete failed for " + table.name + ": " + ex.getMessage());
        }
    }

    static String sha256(Path path) throws IOException {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (java.io.InputStream input = Files.newInputStream(path)) {
                byte[] buffer = new byte[1024 * 1024];
                int read;
                while ((read = input.read(buffer)) >= 0) {
                    if (read > 0) {
                        digest.update(buffer, 0, read);
                    }
                }
            }
            return hexDigest(digest.digest());
        } catch (java.security.NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is unavailable", ex);
        }
    }

    static String hexDigest(byte[] digest) {
        StringBuilder output = new StringBuilder(digest.length * 2);
        for (byte value : digest) {
            output.append(String.format("%02x", value));
        }
        return output.toString();
    }

    static SourceFingerprint sourceFingerprint(Args args, Table table) throws IOException {
        Path path = sourcePath(args, table);
        String cacheKey = path.toAbsolutePath().normalize().toString();
        SourceFingerprint existing = args.sourceFingerprints.get(cacheKey);
        if (existing != null) {
            return existing;
        }
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long rows = 0;
            try (java.io.InputStream input = Files.newInputStream(path);
                 DigestInputStream digestInput = new DigestInputStream(input, digest);
                 BufferedReader reader = new BufferedReader(
                         new java.io.InputStreamReader(digestInput, StandardCharsets.UTF_8));
                 CSVParser parser = CSVFormat.DEFAULT
                         .withFirstRecordAsHeader()
                         .withIgnoreEmptyLines(true)
                         .parse(reader)) {
                for (CSVRecord ignored : parser) {
                    rows++;
                }
            }
            SourceFingerprint fingerprint = new SourceFingerprint(rows, hexDigest(digest.digest()));
            args.sourceFingerprints.put(cacheKey, fingerprint);
            return fingerprint;
        } catch (java.security.NoSuchAlgorithmException ex) {
            throw new IllegalStateException("SHA-256 is unavailable", ex);
        }
    }

    static String sha256Text(String value) throws IOException {
        Path temporary = Files.createTempFile("grbench-sha256-", ".txt");
        try {
            Files.writeString(temporary, value, StandardCharsets.UTF_8);
            return sha256(temporary);
        } finally {
            Files.deleteIfExists(temporary);
        }
    }

    static void markCompleteFromSource(
            Args args,
            ODatabaseSession db,
            Table table,
            long sourceRows,
            long loadedRows,
            long skippedRows,
            long placeholderRows,
            String orphanEdgeMode,
            boolean sourceRowsVerified) throws IOException {
        Path path = sourcePath(args, table);
        SourceFingerprint fingerprint = args.sourceFingerprints.get(
                path.toAbsolutePath().normalize().toString());
        markComplete(
                db,
                table,
                sourceRows,
                loadedRows,
                skippedRows,
                placeholderRows,
                orphanEdgeMode,
                "csv",
                path.toAbsolutePath().normalize().toString(),
                fingerprint == null ? sha256(path) : fingerprint.sha256,
                sourceRowsVerified,
                args.loaderConfigSha256);
    }

    static void markPrefixResumeProvenance(
            ODatabaseSession db, Table table, long resumePrefixRows) {
        db.command(
                "UPDATE _LoadManifest SET resume_mode = ?, resume_prefix_rows = ?, "
                        + "resume_prefix_assumption = ? WHERE class_name = ?",
                "committed_source_prefix_append",
                resumePrefixRows,
                "one_source_row_per_existing_edge_and_zero_prior_skips",
                table.name).close();
    }

    static void truncateClass(ODatabaseSession db, Table table) {
        try {
            if (table.isEdge()) {
                db.command("DELETE EDGE " + table.name).close();
            } else {
                String unsafe = table.isVertex() ? " UNSAFE" : "";
                db.command("TRUNCATE CLASS " + table.name + unsafe).close();
            }
        } catch (Exception ex) {
            try {
                if (table.isEdge()) {
                    db.command("DELETE FROM " + table.name + " UNSAFE").close();
                } else {
                    db.command("DELETE FROM " + table.name + (table.isVertex() ? " UNSAFE" : "")).close();
                }
            } catch (Exception deleteEx) {
                System.err.println("WARN failed to clear class " + table.name + ": " + deleteEx.getMessage());
            }
        }
        try {
            db.command("DELETE FROM _LoadManifest WHERE class_name = ?", table.name).close();
        } catch (Exception ignored) {
        }
    }

    static void replaceDerivedUpdateClass(ODatabaseSession db, Table table) {
        if (db.getMetadata().getSchema().existsClass(table.name)) {
            String staleName = table.name + "__stale_" + System.currentTimeMillis();
            try {
                db.command("ALTER CLASS " + table.name + " NAME " + staleName + " UNSAFE").close();
            } catch (Exception ex) {
                throw new IllegalStateException("failed to rotate derived Update class " + table.name, ex);
            }
        }
        OSchema schema = db.getMetadata().getSchema();
        OClass cls = schema.createClass(table.name, 1);
        for (Column column : table.columns) {
            cls.createProperty(column.name, otype(column.type));
        }
        try {
            db.command("DELETE FROM _LoadManifest WHERE class_name = ?", table.name).close();
        } catch (Exception ignored) {
        }
    }

    static long countRows(Args args, Table table) throws IOException {
        Path path = sourcePath(args, table);
        if (!Files.exists(path)) {
            return 0;
        }
        return sourceFingerprint(args, table).rows;
    }

    static long maybeCountRows(Args args, Table table) throws IOException {
        if (args.skipSourceCount && args.maxRows <= 0) {
            return -1;
        }
        return countRows(args, table);
    }

    static long manifestSourceRows(long sourceRows, long loadedRows) {
        return sourceRows >= 0 ? sourceRows : loadedRows;
    }

    static void setProperties(OElement element, Table table, CSVRecord record) {
        for (Column col : table.columns) {
            String origin = originFor(table, col.name);
            String raw = null;
            if (record.isMapped(origin)) {
                raw = record.get(origin);
            } else if (record.isMapped(col.name)) {
                raw = record.get(col.name);
            }
            Object value = parseValue(raw, col.type);
            if (value != null) {
                element.setProperty(col.name, value);
            }
        }
    }

    static CSVParser openCsv(Path path) throws IOException {
        BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8);
        return CSVFormat.DEFAULT.withFirstRecordAsHeader().withIgnoreEmptyLines(true).parse(reader);
    }

    static void commitIfNeeded(ODatabaseSession db, int[] batchCount, int batchSize) {
        if (batchCount[0] >= batchSize) {
            db.commit();
            db.begin();
            batchCount[0] = 0;
        }
    }

    static void loadVertices(Args args, ODatabaseSession db, List<Table> tables, Map<String, Map<String, ORID>> ridMaps)
            throws IOException {
        for (Table table : tables) {
            if (!table.isVertex()) {
                continue;
            }
            if (!shouldVisitVertexForOnlyClass(args, tables, table)) {
                continue;
            }
            Path path = sourcePath(args, table);
            if (!Files.exists(path)) {
                System.err.println("WARN missing vertex CSV for " + table.name + ": " + path);
                continue;
            }
            long sourceRows = maybeCountRows(args, table);
            if (args.resume && isComplete(args, db, table)) {
                System.out.println("SKIP complete vertex " + table.name);
                Map<String, ORID> map = new HashMap<>();
                ridMaps.put(table.name + "." + table.primaryKey, map);
                for (com.orientechnologies.orient.core.record.impl.ODocument doc : db.browseClass(table.name)) {
                    Object key = doc.getProperty(table.primaryKey);
                    if (key != null) {
                        map.putIfAbsent(key.toString(), doc.getIdentity().copy());
                    }
                }
                System.out.println("DONE vertex map " + table.name + " keys=" + map.size());
                long classRows = db.countClass(table.name);
                markCompleteFromSource(
                        args,
                        db,
                        table,
                        manifestSourceRows(sourceRows, classRows),
                        classRows,
                        0,
                        0,
                        "not_applicable",
                        sourceRows >= 0 && !args.skipSourceCount);
                continue;
            }
            if (args.resume && db.countClass(table.name) > 0) {
                System.out.println("RELOAD partial vertex " + table.name);
                truncateClass(db, table);
            }
            System.out.println("LOAD vertex " + table.name + " from " + path);
            Map<String, ORID> map = new HashMap<>();
            ridMaps.put(table.name + "." + table.primaryKey, map);
            int[] batchCount = {0};
            List<PendingRid> pending = new ArrayList<>();
            long loaded = 0;
            db.begin();
            try (CSVParser parser = openCsv(path)) {
                for (CSVRecord record : parser) {
                    OVertex vertex = db.newVertex(table.name);
                    setProperties(vertex, table, record);
                    vertex.save();
                    Object key = vertex.getProperty(table.primaryKey);
                    if (key != null) {
                        pending.add(new PendingRid(key.toString(), vertex));
                    }
                    loaded++;
                    batchCount[0]++;
                    if (batchCount[0] >= args.batchSize) {
                        db.commit();
                        for (PendingRid p : pending) {
                            map.putIfAbsent(p.key, p.vertex.getIdentity().copy());
                        }
                        pending.clear();
                        db.begin();
                        batchCount[0] = 0;
                    }
                    if (args.maxRows > 0 && loaded >= args.maxRows) {
                        break;
                    }
                    if (loaded % 100000 == 0) {
                        System.out.println("  " + table.name + " rows=" + loaded);
                    }
                }
            }
            db.commit();
            for (PendingRid p : pending) {
                map.putIfAbsent(p.key, p.vertex.getIdentity().copy());
            }
            System.out.println("DONE vertex " + table.name + " rows=" + loaded + " keys=" + map.size());
            markCompleteFromSource(
                    args,
                    db,
                    table,
                    manifestSourceRows(sourceRows, loaded),
                    loaded,
                    0,
                    0,
                    "not_applicable",
                    sourceRows >= 0 && args.maxRows <= 0 && !args.skipSourceCount);
        }
    }

    static void loadPlainTables(Args args, ODatabaseSession db, List<Table> tables) throws IOException {
        for (Table table : tables) {
            if (!table.isPlain()) {
                continue;
            }
            if (!args.onlyClass.isEmpty() && !args.onlyClass.equals(table.name)) {
                continue;
            }
            if (args.skipUpdates && "UPDATE".equals(table.source)) {
                continue;
            }
            if ("UPDATE".equals(table.source) && "derived".equals(args.updateSourceMode)) {
                continue;
            }
            Path path = sourcePath(args, table);
            if (!Files.exists(path)) {
                System.err.println("WARN missing plain CSV for " + table.name + ": " + path);
                continue;
            }
            long sourceRows = maybeCountRows(args, table);
            if (args.resume && isComplete(args, db, table)) {
                System.out.println("SKIP complete document " + table.name);
                long classRows = db.countClass(table.name);
                markCompleteFromSource(
                        args,
                        db,
                        table,
                        manifestSourceRows(sourceRows, classRows),
                        classRows,
                        0,
                        0,
                        "not_applicable",
                        sourceRows >= 0 && args.maxRows <= 0 && !args.skipSourceCount);
                continue;
            }
            long resumeRows = 0;
            if (args.resume) {
                resumeRows = db.countClass(table.name);
                if (resumeRows > 0) {
                    System.out.println("RESUME partial document " + table.name + " existing_rows=" + resumeRows);
                }
            }
            System.out.println("LOAD document " + table.name + " from " + path);
            int[] batchCount = {0};
            long loaded = resumeRows;
            db.begin();
            try (CSVParser parser = openCsv(path)) {
                for (CSVRecord record : parser) {
                    if (resumeRows > 0 && record.getRecordNumber() <= resumeRows) {
                        continue;
                    }
                    OElement doc = db.newElement(table.name);
                    setProperties(doc, table, record);
                    doc.save();
                    loaded++;
                    batchCount[0]++;
                    commitIfNeeded(db, batchCount, args.batchSize);
                    if (args.maxRows > 0 && loaded >= args.maxRows) {
                        break;
                    }
                    if (loaded % 100000 == 0) {
                        System.out.println("  " + table.name + " rows=" + loaded);
                    }
                }
            }
            db.commit();
            System.out.println("DONE document " + table.name + " rows=" + loaded);
            markCompleteFromSource(
                    args,
                    db,
                    table,
                    manifestSourceRows(sourceRows, loaded),
                    loaded,
                    0,
                    0,
                    "not_applicable",
                    sourceRows >= 0 && args.maxRows <= 0 && !args.skipSourceCount);
        }
    }

    static Optional<OVertex> vertexByRid(ODatabaseSession db, ORID rid) {
        ORecord record = db.load(rid);
        if (record instanceof OElement) {
            return ((OElement) record).asVertex();
        }
        return Optional.empty();
    }

    static String placeholderCacheKey(String targetClass, String targetKey, String targetValue) {
        return targetClass + "\u0000" + targetKey + "\u0000" + targetValue;
    }

    static OVertex placeholderVertex(
            ODatabaseSession db,
            Map<String, OVertex> placeholders,
            String targetClass,
            String targetKey,
            String targetValue) {
        String cacheKey = placeholderCacheKey(targetClass, targetKey, targetValue);
        OVertex existing = placeholders.get(cacheKey);
        if (existing != null) {
            return existing;
        }
        OVertex vertex = db.newVertex("_MissingEndpoint");
        vertex.setProperty("target_class", targetClass);
        vertex.setProperty("target_key", targetKey);
        vertex.setProperty("target_value", targetValue);
        vertex.save();
        placeholders.put(cacheKey, vertex);
        return vertex;
    }

    static boolean needsPlaceholderReload(Args args, ODatabaseSession db, Table table) {
        if (!table.isEdge() || !"placeholder".equals(args.orphanEdgeMode)) {
            return false;
        }
        String sql = "SELECT source_rows,loaded_rows FROM _LoadManifest "
                + "WHERE class_name = ? AND status = 'DONE' LIMIT 1";
        try (com.orientechnologies.orient.core.sql.executor.OResultSet rs = db.query(sql, table.name)) {
            if (!rs.hasNext()) {
                return true;
            }
            com.orientechnologies.orient.core.sql.executor.OResult row = rs.next();
            Number sourceRows = row.getProperty("source_rows");
            Number loadedRows = row.getProperty("loaded_rows");
            return sourceRows == null || loadedRows == null || sourceRows.longValue() != loadedRows.longValue();
        } catch (Exception ex) {
            return true;
        }
    }

    static long existingManifestSourceRows(ODatabaseSession db, Table table) {
        String sql = "SELECT source_rows FROM _LoadManifest WHERE class_name = ? LIMIT 1";
        try (com.orientechnologies.orient.core.sql.executor.OResultSet rs = db.query(sql, table.name)) {
            if (rs.hasNext()) {
                Number value = rs.next().getProperty("source_rows");
                return value == null ? -1 : value.longValue();
            }
        } catch (Exception ignored) {
        }
        return -1;
    }

    static void loadEdges(Args args, ODatabaseSession db, List<Table> tables, Map<String, Map<String, ORID>> ridMaps)
            throws IOException {
        Map<String, OVertex> placeholders = new HashMap<>();
        for (com.orientechnologies.orient.core.record.impl.ODocument doc : db.browseClass("_MissingEndpoint")) {
            String targetClass = doc.getProperty("target_class");
            String targetKey = doc.getProperty("target_key");
            String targetValue = doc.getProperty("target_value");
            Optional<OVertex> vertex = doc.asVertex();
            if (targetClass != null && targetKey != null && targetValue != null && vertex.isPresent()) {
                placeholders.putIfAbsent(
                        placeholderCacheKey(targetClass, targetKey, targetValue),
                        vertex.get());
            }
        }
        for (Table table : tables) {
            if (!table.isEdge()) {
                continue;
            }
            if (!args.onlyClass.isEmpty() && !args.onlyClass.equals(table.name)) {
                continue;
            }
            Path path = sourcePath(args, table);
            if (!Files.exists(path)) {
                System.err.println("WARN missing edge CSV for " + table.name + ": " + path);
                continue;
            }
            long sourceRows = maybeCountRows(args, table);
            if (sourceRows < 0 && args.repairSkippedEdges) {
                sourceRows = existingManifestSourceRows(db, table);
            }
            if (args.resume && isComplete(args, db, table) && !needsPlaceholderReload(args, db, table)) {
                System.out.println("SKIP complete edge " + table.name);
                continue;
            }
            long existingRows = args.resume ? db.countClass(table.name) : 0;
            boolean repairOnly = args.repairSkippedEdges && existingRows > 0;
            boolean prefixResume = args.resume
                    && existingRows > 0
                    && args.resumePartialEdgePrefixes.contains(table.name);
            long resumePrefixRows = prefixResume ? existingRows : 0;
            if (prefixResume && repairOnly) {
                throw new IllegalArgumentException(
                        "prefix edge resume cannot be combined with skipped-edge repair: " + table.name);
            }
            if (prefixResume) {
                if (!"placeholder".equals(args.orphanEdgeMode)) {
                    throw new IllegalArgumentException(
                            "prefix edge resume requires --orphan-edge-mode placeholder: " + table.name);
                }
                if (sourceRows >= 0 && resumePrefixRows > sourceRows) {
                    throw new IllegalStateException(
                            "existing edge count exceeds source rows for " + table.name
                                    + ": existing=" + resumePrefixRows + ",source=" + sourceRows);
                }
                System.out.println(
                        "RESUME committed source-prefix edge " + table.name
                                + " prefix_rows=" + resumePrefixRows);
            } else if (args.resume && existingRows > 0 && !repairOnly) {
                System.out.println("RELOAD partial edge " + table.name);
                truncateClass(db, table);
                existingRows = 0;
            } else if (repairOnly) {
                System.out.println("REPAIR skipped edge rows " + table.name + " existing_rows=" + existingRows);
            }
            Map<String, ORID> fromMap = ridMaps.get(table.fromVertex + "." + table.fromPk);
            Map<String, ORID> toMap = ridMaps.get(table.toVertex + "." + table.toPk);
            if (fromMap == null || toMap == null) {
                System.err.println("WARN missing endpoint map for edge " + table.name);
                continue;
            }
            System.out.println("LOAD edge " + table.name + " from " + path);
            int[] batchCount = {0};
            long loaded = existingRows;
            long skipped = 0;
            long placeholderRows = 0;
            long visited = 0;
            db.begin();
            try (CSVParser parser = openCsv(path)) {
                for (CSVRecord record : parser) {
                    visited++;
                    if (visited <= resumePrefixRows) {
                        if (visited % 1000000 == 0) {
                            System.out.println(
                                    "  " + table.name + " verified_prefix_rows=" + visited
                                            + "/" + resumePrefixRows);
                        }
                        continue;
                    }
                    String fromValue = record.isMapped(originFor(table, table.fromCol))
                            ? record.get(originFor(table, table.fromCol)).trim()
                            : "";
                    String toValue = record.isMapped(originFor(table, table.toCol))
                            ? record.get(originFor(table, table.toCol)).trim()
                            : "";
                    ORID fromRid = fromMap.get(fromValue);
                    ORID toRid = toMap.get(toValue);
                    Optional<OVertex> from = fromRid == null ? Optional.empty() : vertexByRid(db, fromRid);
                    Optional<OVertex> to = toRid == null ? Optional.empty() : vertexByRid(db, toRid);
                    boolean missingEndpoint = !from.isPresent() || !to.isPresent();
                    boolean shouldProcess = !repairOnly || missingEndpoint;
                    if (shouldProcess) {
                        if (missingEndpoint && !"placeholder".equals(args.orphanEdgeMode)) {
                            skipped++;
                        } else {
                            OVertex fromVertex = from.orElseGet(
                                    () -> placeholderVertex(
                                            db, placeholders, table.fromVertex, table.fromPk, fromValue));
                            OVertex toVertex = to.orElseGet(
                                    () -> placeholderVertex(
                                            db, placeholders, table.toVertex, table.toPk, toValue));
                            OEdge edge = db.newEdge(fromVertex, toVertex, table.name);
                            setProperties(edge, table, record);
                            edge.save();
                            loaded++;
                            if (missingEndpoint) {
                                placeholderRows++;
                            }
                            batchCount[0]++;
                            commitIfNeeded(db, batchCount, args.batchSize);
                        }
                    }
                    if (args.maxRows > 0 && visited >= args.maxRows) {
                        break;
                    }
                    if (visited % 100000 == 0) {
                        System.out.println("  " + table.name + " visited=" + visited + " rows=" + loaded
                                + " skipped=" + skipped + " placeholder_rows=" + placeholderRows);
                    }
                }
            }
            db.commit();
            if (sourceRows >= 0 && args.maxRows <= 0 && loaded + skipped != sourceRows) {
                throw new IllegalStateException(
                        "edge repair count mismatch for " + table.name + ": source=" + sourceRows
                                + " loaded=" + loaded + " skipped=" + skipped);
            }
            System.out.println("DONE edge " + table.name + " rows=" + loaded + " skipped=" + skipped
                    + " placeholder_rows=" + placeholderRows + " orphan_edge_mode=" + args.orphanEdgeMode);
            markCompleteFromSource(
                    args,
                    db,
                    table,
                    manifestSourceRows(sourceRows, loaded + skipped),
                    loaded,
                    skipped,
                    placeholderRows,
                    args.orphanEdgeMode,
                    sourceRows >= 0 && args.maxRows <= 0 && !args.skipSourceCount);
            if (prefixResume) {
                markPrefixResumeProvenance(db, table, resumePrefixRows);
            }
        }
    }

    static void createIndexes(ODatabaseSession db, Map<String, Set<String>> indexes) {
        try {
            db.command(
                    "CREATE INDEX _MissingEndpoint_lookup_idx ON _MissingEndpoint "
                            + "(target_class,target_key,target_value) UNIQUE").close();
            System.out.println("INDEX _MissingEndpoint.(target_class,target_key,target_value)");
        } catch (Exception ex) {
            if (ex.getMessage() == null || !ex.getMessage().contains("already exists")) {
                System.err.println("WARN create placeholder index failed: " + ex.getMessage());
            }
        }
        for (Map.Entry<String, Set<String>> entry : indexes.entrySet()) {
            String cls = entry.getKey();
            for (String col : entry.getValue()) {
                String indexName = cls + "_" + col + "_idx";
                String sql = "CREATE INDEX " + indexName + " ON " + cls + " (" + col + ") NOTUNIQUE";
                try {
                    db.command(sql).close();
                    System.out.println("INDEX " + cls + "." + col);
                } catch (Exception ex) {
                    System.err.println("WARN create index failed: " + sql + " :: " + ex.getMessage());
                }
            }
        }
    }

    static Map<String, String> updateDerivationQueries() {
        Map<String, String> queries = new LinkedHashMap<>();
        queries.put("grbench_update1_papers", "SELECT FROM Papers WHERE year BETWEEN 2020 AND 2025");
        String paperCohort = "SELECT paperid FROM grbench_update1_papers";
        queries.put(
                "grbench_update1_papers_to_authors",
                "SELECT FROM Papers_to_Authors WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update2_edges",
                "SELECT FROM PaperReferences WHERE citing_paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_paperreferences",
                "SELECT FROM PaperReferences WHERE citing_paperid IN (" + paperCohort
                        + ") OR cited_paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_papers_to_authors",
                "SELECT FROM grbench_update1_papers_to_authors");
        queries.put(
                "grbench_update3_authors_paper",
                "SELECT FROM grbench_update1_papers_to_authors");
        queries.put(
                "grbench_update3_contributed_from",
                "SELECT FROM contributed_from WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_paperfields",
                "SELECT FROM PaperFields WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_link_nsf",
                "SELECT FROM Link_NSF WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_link_nih",
                "SELECT FROM Link_NIH WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_link_clinicaltrials",
                "SELECT FROM Link_ClinicalTrials WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_link_newsfeed",
                "SELECT FROM link_newsfeed WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update3_link_twitter",
                "SELECT FROM link_twitter WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update4_authors_gender",
                "SELECT FROM Authors_Gender WHERE h_index BETWEEN 10 AND 20");
        String authorCohort = "SELECT authorid FROM grbench_update4_authors_gender";
        queries.put(
                "grbench_update5_papers_to_authors",
                "SELECT FROM Papers_to_Authors WHERE paperid IN (" + paperCohort + ")");
        queries.put(
                "grbench_update6_papers_to_authors",
                "SELECT FROM Papers_to_Authors WHERE authorid IN (" + authorCohort + ")");
        queries.put(
                "grbench_update4_authors_paper",
                "SELECT FROM Authors_Paper WHERE authorid IN (" + authorCohort + ")");
        queries.put(
                "grbench_update6_affiliated_with",
                "SELECT FROM affiliated_with WHERE authorid IN (" + authorCohort + ")");
        return queries;
    }

    static Set<String> derivedIdSet(ODatabaseSession db, String className, String property) {
        Set<String> values = new HashSet<>();
        try (com.orientechnologies.orient.core.sql.executor.OResultSet results =
                     db.query("SELECT " + property + " FROM " + className)) {
            while (results.hasNext()) {
                Object value = results.next().getProperty(property);
                if (value != null) {
                    values.add(value.toString());
                }
            }
        }
        return values;
    }

    static String updateDerivationScanQuery(String tableName, String logicalQuery) {
        Map<String, String> scans = new HashMap<>();
        scans.put("grbench_update1_papers_to_authors", "SELECT FROM Papers_to_Authors");
        scans.put("grbench_update2_edges", "SELECT FROM PaperReferences");
        scans.put("grbench_update3_paperreferences", "SELECT FROM PaperReferences");
        scans.put("grbench_update3_contributed_from", "SELECT FROM contributed_from");
        scans.put("grbench_update3_paperfields", "SELECT FROM PaperFields");
        scans.put("grbench_update3_link_nsf", "SELECT FROM Link_NSF");
        scans.put("grbench_update3_link_nih", "SELECT FROM Link_NIH");
        scans.put("grbench_update3_link_clinicaltrials", "SELECT FROM Link_ClinicalTrials");
        scans.put("grbench_update3_link_newsfeed", "SELECT FROM link_newsfeed");
        scans.put("grbench_update3_link_twitter", "SELECT FROM link_twitter");
        scans.put("grbench_update5_papers_to_authors", "SELECT FROM Papers_to_Authors");
        scans.put("grbench_update4_authors_paper", "SELECT FROM Authors_Paper");
        scans.put("grbench_update6_papers_to_authors", "SELECT FROM Papers_to_Authors");
        scans.put("grbench_update6_affiliated_with", "SELECT FROM affiliated_with");
        return scans.getOrDefault(tableName, logicalQuery);
    }

    static boolean includeDerivedRow(
            String tableName,
            OElement source,
            Set<String> paperIds,
            Set<String> authorIds) {
        if (tableName.equals("grbench_update2_edges")) {
            Object value = source.getProperty(sourcePropertyName(source, "citing_paperid"));
            return value != null && paperIds.contains(value.toString());
        }
        if (tableName.equals("grbench_update3_paperreferences")) {
            Object citing = source.getProperty(sourcePropertyName(source, "citing_paperid"));
            Object cited = source.getProperty(sourcePropertyName(source, "cited_paperid"));
            return (citing != null && paperIds.contains(citing.toString()))
                    || (cited != null && paperIds.contains(cited.toString()));
        }
        if (tableName.equals("grbench_update1_papers_to_authors")
                || tableName.equals("grbench_update3_contributed_from")
                || tableName.equals("grbench_update3_paperfields")
                || tableName.equals("grbench_update3_link_nsf")
                || tableName.equals("grbench_update3_link_nih")
                || tableName.equals("grbench_update3_link_clinicaltrials")
                || tableName.equals("grbench_update3_link_newsfeed")
                || tableName.equals("grbench_update3_link_twitter")
                || tableName.equals("grbench_update5_papers_to_authors")) {
            Object value = source.getProperty(sourcePropertyName(source, "paperid"));
            return value != null && paperIds.contains(value.toString());
        }
        if (tableName.equals("grbench_update4_authors_paper")
                || tableName.equals("grbench_update6_papers_to_authors")
                || tableName.equals("grbench_update6_affiliated_with")) {
            Object value = source.getProperty(sourcePropertyName(source, "authorid"));
            return value != null && authorIds.contains(value.toString());
        }
        return true;
    }

    static String sourcePropertyName(OElement source, String requested) {
        for (String propertyName : source.getPropertyNames()) {
            if (propertyName.equalsIgnoreCase(requested)) {
                return propertyName;
            }
        }
        return requested;
    }

    static void copyDerivedProperties(OElement source, OElement target, Table table) {
        for (Column column : table.columns) {
            String sourceName = sourcePropertyName(source, column.name);
            if (!source.hasProperty(sourceName)) {
                continue;
            }
            Object value = source.getProperty(sourceName);
            if (value != null) {
                target.setProperty(column.name, value);
            }
        }
    }

    static void markDerivedUpdateComplete(Args args, ODatabaseSession db, Table table, long rows, String derivationQuery)
            throws IOException {
        markComplete(
                db,
                table,
                rows,
                rows,
                0,
                0,
                "not_applicable",
                "derived_database_snapshot",
                "database-derived:" + table.name,
                sha256Text(derivationQuery + "\nrows=" + rows),
                args.maxRows <= 0,
                args.loaderConfigSha256);
        try {
            db.command(
                    "UPDATE _LoadManifest SET loader_mode = 'derived_update_snapshot_v1' "
                            + "WHERE class_name = ?",
                    table.name).close();
        } catch (Exception ex) {
            throw new IllegalStateException("failed to record derived Update provenance for " + table.name, ex);
        }
    }

    static void deriveUpdateSnapshots(Args args, ODatabaseSession db, List<Table> tables) throws IOException {
        Set<String> paperIds = null;
        Set<String> authorIds = null;
        for (Map.Entry<String, String> entry : updateDerivationQueries().entrySet()) {
            Table table = findTable(tables, entry.getKey());
            if (table == null) {
                throw new IllegalStateException("missing Update staging config for " + entry.getKey());
            }
            if (!args.onlyClass.isEmpty() && !args.onlyClass.equals(table.name)) {
                continue;
            }
            if (!args.deriveClasses.isEmpty() && !args.deriveClasses.contains(table.name)) {
                continue;
            }
            replaceDerivedUpdateClass(db, table);
            long loaded = 0;
            int[] batchCount = {0};
            String scanQuery = updateDerivationScanQuery(table.name, entry.getValue());
            if (!scanQuery.equals(entry.getValue()) && paperIds == null
                    && !table.name.startsWith("grbench_update4_")
                    && !table.name.startsWith("grbench_update6_")) {
                paperIds = derivedIdSet(db, "grbench_update1_papers", "paperid");
            }
            if (!scanQuery.equals(entry.getValue()) && authorIds == null
                    && (table.name.startsWith("grbench_update4_")
                    || table.name.startsWith("grbench_update6_"))) {
                authorIds = derivedIdSet(db, "grbench_update4_authors_gender", "authorid");
            }
            System.out.println("DERIVE document " + table.name + " from: " + entry.getValue());
            db.begin();
            try (com.orientechnologies.orient.core.sql.executor.OResultSet results = db.query(scanQuery)) {
                while (results.hasNext()) {
                    com.orientechnologies.orient.core.sql.executor.OResult result = results.next();
                    if (!result.isElement()) {
                        throw new IllegalStateException("derived Update query did not return elements: " + table.name);
                    }
                    OElement source = result.toElement();
                    if (!includeDerivedRow(table.name, source, paperIds, authorIds)) {
                        continue;
                    }
                    OElement target = db.newElement(table.name);
                    copyDerivedProperties(source, target, table);
                    target.save();
                    loaded++;
                    batchCount[0]++;
                    commitIfNeeded(db, batchCount, args.batchSize);
                    if (args.maxRows > 0 && loaded >= args.maxRows) {
                        break;
                    }
                    if (loaded % 100000 == 0) {
                        System.out.println("  " + table.name + " rows=" + loaded);
                    }
                }
            }
            db.commit();
            markDerivedUpdateComplete(args, db, table, loaded, entry.getValue());
            System.out.println("DONE derived document " + table.name + " rows=" + loaded);
        }
    }

    static void printCounts(ODatabaseSession db, List<Table> tables) {
        for (Table table : tables) {
            try {
                System.out.println("COUNT " + table.name + "=" + db.countClass(table.name));
            } catch (Exception ex) {
                System.err.println("WARN count failed for " + table.name + ": " + ex.getMessage());
            }
        }
    }

    public static void main(String[] argv) throws Exception {
        Args args = parseArgs(argv);
        List<Table> tables = readTables(args.configDir);
        Map<String, Set<String>> indexes = readIndexes(args.configDir);
        args.loaderConfigSha256 = sha256Text(
                Files.readString(args.configDir.resolve("tables.tsv"), StandardCharsets.UTF_8)
                        + "\n--indexes.tsv--\n"
                        + Files.readString(args.configDir.resolve("indexes.tsv"), StandardCharsets.UTF_8));
        args.compatibleLoaderConfigSha256s.add(args.loaderConfigSha256);
        if (!args.onlyClass.isEmpty() && tables.stream().noneMatch(t -> args.onlyClass.equals(t.name))) {
            throw new IllegalArgumentException("unknown --only-class: " + args.onlyClass);
        }
        for (String className : args.deriveClasses) {
            if (tables.stream().noneMatch(t -> className.equals(t.name))) {
                throw new IllegalArgumentException("unknown --derive-classes entry: " + className);
            }
        }
        for (String className : args.resumePartialEdgePrefixes) {
            if (tables.stream().noneMatch(t -> className.equals(t.name) && t.isEdge())) {
                throw new IllegalArgumentException(
                        "unknown or non-edge --resume-partial-edge-prefixes entry: " + className);
            }
        }
        if (!args.onlyClass.isEmpty()) {
            indexes.keySet().removeIf(cls -> !args.onlyClass.equals(cls));
        }
        if (!Files.isDirectory(args.dbRoot)) {
            Files.createDirectories(args.dbRoot);
        }

        try (OrientDB orient = new OrientDB("embedded:" + args.dbRoot.toAbsolutePath(), OrientDBConfig.defaultConfig())) {
            if (!orient.exists(args.sf)) {
                throw new IllegalStateException("database does not exist; create it first with OrientDB console: " + args.sf);
            }
            try (ODatabaseSession db = orient.open(
                    args.sf,
                    requireEnvironment("ORIENTDB_USERNAME"),
                    requireEnvironment("ORIENTDB_PASSWORD"))) {
                createSchema(db, tables);
                if (args.deriveUpdatesOnly) {
                    deriveUpdateSnapshots(args, db, tables);
                    if (!args.skipFinalCounts) {
                        printCounts(db, tables);
                    }
                    return;
                }
                Map<String, Map<String, ORID>> ridMaps = new HashMap<>();
                loadVertices(args, db, tables, ridMaps);
                loadPlainTables(args, db, tables);
                loadEdges(args, db, tables, ridMaps);
                createIndexes(db, indexes);
                if (!args.skipUpdates && "derived".equals(args.updateSourceMode) && args.onlyClass.isEmpty()) {
                    deriveUpdateSnapshots(args, db, tables);
                }
                if (!args.skipFinalCounts) {
                    printCounts(db, tables);
                }
            }
        }
    }
}
