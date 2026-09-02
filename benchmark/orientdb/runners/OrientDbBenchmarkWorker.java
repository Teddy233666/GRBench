import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Array;
import java.lang.management.ManagementFactory;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Base64;
import java.util.Collections;
import java.util.Date;
import java.util.Iterator;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;
import java.util.Set;
import java.util.stream.Stream;

import com.orientechnologies.orient.core.db.ODatabaseSession;
import com.orientechnologies.orient.core.db.OrientDB;
import com.orientechnologies.orient.core.db.OrientDBConfig;
import com.orientechnologies.orient.core.db.record.OIdentifiable;
import com.orientechnologies.orient.core.id.ORID;
import com.orientechnologies.orient.core.id.ORecordId;
import com.orientechnologies.orient.core.index.OIndex;
import com.orientechnologies.orient.core.record.OElement;
import com.orientechnologies.orient.core.record.OEdge;
import com.orientechnologies.orient.core.record.ORecord;
import com.orientechnologies.orient.core.record.OVertex;
import com.orientechnologies.orient.core.metadata.schema.OClass;
import com.orientechnologies.orient.core.metadata.schema.OType;
import com.orientechnologies.orient.core.sql.executor.OResult;
import com.orientechnologies.orient.core.sql.executor.OResultSet;

public class OrientDbBenchmarkWorker {
    private static final String PROTOCOL_VERSION = "4";
    private static final String READY = "GRBENCH_READY";
    private static final String EXEC = "GRBENCH_EXEC";
    private static final String UPDATE = "GRBENCH_UPDATE";
    private static final String START = "GRBENCH_START";
    private static final String RESULT = "GRBENCH_RESULT";
    private static final String CLOSE = "GRBENCH_CLOSE";
    private static final String UPDATE6_AUTHOR_SHADOW = "_GrbenchUpdate6AuthorShadow";
    private static final String UPDATE6_AUTHOR_SHADOW_INDEX =
            "_GrbenchUpdate6AuthorShadow_authorid_idx";
    private static final String UPDATE_RECOVERY_PROGRESS =
            "_GrbenchUpdateRecoveryProgress";
    private static final String UPDATE_RECOVERY_PROGRESS_INDEX =
            "_GrbenchUpdateRecoveryProgress_operation_target_staging_idx";
    private static final Map<String, Optional<OIndex>> PROPERTY_INDEX_CACHE = new HashMap<>();
    private static final com.sun.management.OperatingSystemMXBean OPERATING_SYSTEM =
            (com.sun.management.OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean();

    static String requireEnvironment(String name) {
        String value = System.getenv(name);
        if (value == null || value.isEmpty()) {
            throw new IllegalStateException(name + " must be set in the process environment");
        }
        return value;
    }

    static class Args {
        String dbRoot;
        String database;
        int maxResultRows = 1_000_000;
    }

    static class MaterializedResultSet {
        final Set<String> columns = new LinkedHashSet<>();
        final List<Map<String, Object>> rows = new ArrayList<>();
    }

    static class ExecutionResult {
        final List<MaterializedResultSet> resultSets = new ArrayList<>();
        int rowCount;
    }

    static class UpdateSpec {
        final String targetClass;
        final String stagingClass;
        final List<String> matchProperties;
        final String fromClass;
        final String fromKey;
        final String fromValueProperty;
        final String toClass;
        final String toKey;
        final String toValueProperty;

        UpdateSpec(
                String targetClass,
                String stagingClass,
                List<String> matchProperties,
                String fromClass,
                String fromKey,
                String fromValueProperty,
                String toClass,
                String toKey,
                String toValueProperty) {
            this.targetClass = targetClass;
            this.stagingClass = stagingClass;
            this.matchProperties = matchProperties;
            this.fromClass = fromClass;
            this.fromKey = fromKey;
            this.fromValueProperty = fromValueProperty;
            this.toClass = toClass;
            this.toKey = toKey;
            this.toValueProperty = toValueProperty;
        }

        boolean isEdge() {
            return fromClass != null;
        }
    }

    static class UpdateExecutionResult {
        long modifiedRows;
        long visitedRows;
        long missingRows;
        long committedBatches;

        void add(UpdateExecutionResult other) {
            modifiedRows += other.modifiedRows;
            visitedRows += other.visitedRows;
            missingRows += other.missingRows;
            committedBatches += other.committedBatches;
        }
    }

    static UpdateSpec vertexSpec(String targetClass, String stagingClass, String matchProperty) {
        return new UpdateSpec(
                targetClass,
                stagingClass,
                Collections.singletonList(matchProperty),
                null,
                null,
                null,
                null,
                null,
                null);
    }

    static UpdateSpec edgeSpec(
            String targetClass,
            String stagingClass,
            List<String> matchProperties,
            String fromClass,
            String fromKey,
            String fromValueProperty,
            String toClass,
            String toKey,
            String toValueProperty) {
        return new UpdateSpec(
                targetClass,
                stagingClass,
                matchProperties,
                fromClass,
                fromKey,
                fromValueProperty,
                toClass,
                toKey,
                toValueProperty);
    }

    static UpdateSpec paperReferences(String stagingClass) {
        return edgeSpec(
                "PaperReferences",
                stagingClass,
                List.of("citing_paperid", "cited_paperid"),
                "Papers",
                "paperid",
                "citing_paperid",
                "Papers",
                "paperid",
                "cited_paperid");
    }

    static UpdateSpec papersToAuthors(String targetClass, String stagingClass) {
        return edgeSpec(
                targetClass,
                stagingClass,
                List.of("paperid", "authorid"),
                "Papers",
                "paperid",
                "paperid",
                "Authors_Gender",
                "authorid",
                "authorid");
    }

    static UpdateSpec authorsPaper(String stagingClass) {
        return edgeSpec(
                "Authors_Paper",
                stagingClass,
                List.of("paperid", "authorid"),
                "Authors_Gender",
                "authorid",
                "authorid",
                "Papers",
                "paperid",
                "paperid");
    }

    static List<UpdateSpec> paperCascadeSpecs() {
        return List.of(
                paperReferences("grbench_update3_paperreferences"),
                papersToAuthors("Papers_to_Authors", "grbench_update1_papers_to_authors"),
                authorsPaper("grbench_update3_authors_paper"),
                edgeSpec(
                        "contributed_from",
                        "grbench_update3_contributed_from",
                        List.of("paperid", "institution_id", "authorid"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "Affiliations",
                        "institutionid",
                        "institution_id"),
                edgeSpec(
                        "PaperFields",
                        "grbench_update3_paperfields",
                        List.of("paperid", "fieldid"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "Fields",
                        "fieldid",
                        "fieldid"),
                edgeSpec(
                        "Link_NSF",
                        "grbench_update3_link_nsf",
                        List.of("paperid", "award_id"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "NSF_Metadata",
                        "award_id",
                        "award_id"),
                edgeSpec(
                        "Link_NIH",
                        "grbench_update3_link_nih",
                        List.of("paperid", "award_id"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "NIH_Metadata",
                        "award_id",
                        "award_id"),
                edgeSpec(
                        "Link_ClinicalTrials",
                        "grbench_update3_link_clinicaltrials",
                        List.of("paperid", "nct_id"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "clinicaltrials_metadata",
                        "nct_id",
                        "nct_id"),
                edgeSpec(
                        "link_newsfeed",
                        "grbench_update3_link_newsfeed",
                        List.of("paperid", "newsfeed_id"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "Newsfeed_Metadata",
                        "newsfeed_id",
                        "newsfeed_id"),
                edgeSpec(
                        "link_twitter",
                        "grbench_update3_link_twitter",
                        List.of("paperid", "tweet_id"),
                        "Papers",
                        "paperid",
                        "paperid",
                        "Twitter_Metadata",
                        "tweet_id",
                        "tweet_id"),
                vertexSpec("Papers", "grbench_update1_papers", "paperid"));
    }

    static List<UpdateSpec> authorCascadeSpecs() {
        return List.of(
                papersToAuthors("Papers_to_Authors", "grbench_update6_papers_to_authors"),
                authorsPaper("grbench_update4_authors_paper"),
                edgeSpec(
                        "affiliated_with",
                        "grbench_update6_affiliated_with",
                        List.of("authorid", "institution_id"),
                        "Authors_Gender",
                        "authorid",
                        "authorid",
                        "Affiliations",
                        "institutionid",
                        "institution_id"),
                vertexSpec("Authors_Gender", "grbench_update4_authors_gender", "authorid"));
    }

    static List<UpdateSpec> deleteSpecs(String filename) {
        switch (filename) {
            case "U1a.sql":
            case "U5a.sql":
                return paperCascadeSpecs();
            case "U3a.sql":
                return Collections.singletonList(paperReferences("grbench_update2_edges"));
            case "U2a.sql":
                return authorCascadeSpecs();
            case "U4a.sql":
                return Collections.singletonList(
                        papersToAuthors("Papers_to_Authors", "grbench_update5_papers_to_authors"));
            case "U6a.sql":
                return List.of(
                        papersToAuthors("Papers_to_Authors", "grbench_update6_papers_to_authors"),
                        edgeSpec(
                                "affiliated_with",
                                "grbench_update6_affiliated_with",
                                List.of("authorid", "institution_id"),
                                "Authors_Gender",
                                "authorid",
                                "authorid",
                                "Affiliations",
                                "institutionid",
                                "institution_id"));
            default:
                throw new IllegalArgumentException("unsupported Update delete file: " + filename);
        }
    }

    static List<UpdateSpec> restoreSpecs(String filename) {
        List<UpdateSpec> specs;
        switch (filename) {
            case "U1b.sql":
            case "U5b.sql":
                specs = new ArrayList<>(paperCascadeSpecs());
                break;
            case "U3b.sql":
                return Collections.singletonList(paperReferences("grbench_update2_edges"));
            case "U2b.sql":
                specs = new ArrayList<>(authorCascadeSpecs());
                break;
            case "U4b.sql":
                return Collections.singletonList(
                        papersToAuthors("Papers_to_Authors", "grbench_update5_papers_to_authors"));
            case "U6b.sql":
                specs = new ArrayList<>(deleteSpecs("U6a.sql"));
                break;
            default:
                throw new IllegalArgumentException("unsupported Update restore file: " + filename);
        }
        Collections.reverse(specs);
        return specs;
    }

    static String deleteFilename(String filename) {
        if (filename.endsWith("a.sql")) {
            return filename;
        }
        if (filename.endsWith("b.sql")) {
            return filename.substring(0, filename.length() - 5) + "a.sql";
        }
        throw new IllegalArgumentException("invalid Update filename: " + filename);
    }

    static String restoreFilename(String filename) {
        if (filename.endsWith("b.sql")) {
            return filename;
        }
        if (filename.endsWith("a.sql")) {
            return filename.substring(0, filename.length() - 5) + "b.sql";
        }
        throw new IllegalArgumentException("invalid Update filename: " + filename);
    }

    static Optional<OElement> queryOneElement(
            ODatabaseSession database,
            String query,
            Object... parameters) {
        try (OResultSet results = database.query(query, parameters)) {
            if (!results.hasNext()) {
                return Optional.empty();
            }
            OResult result = results.next();
            return result.isElement() ? Optional.of(result.toElement()) : Optional.empty();
        }
    }

    static Optional<OIndex> propertyIndex(
            ODatabaseSession database,
            String className,
            String property) {
        String cacheKey = className + "\u0000" + property;
        return PROPERTY_INDEX_CACHE.computeIfAbsent(cacheKey, ignored -> {
            OClass schemaClass = database.getMetadata().getSchema().getClass(className);
            if (schemaClass == null) {
                return Optional.empty();
            }
            for (OIndex index : schemaClass.getInvolvedIndexes(property)) {
                if (index.getDefinition() != null
                        && index.getDefinition().getFields().size() == 1
                        && property.equals(index.getDefinition().getFields().get(0))
                        && index.getInternal().canBeUsedInEqualityOperators()) {
                    return Optional.of(index);
                }
            }
            return Optional.empty();
        });
    }

    static Optional<OElement> findIndexedElement(
            ODatabaseSession database,
            String className,
            String property,
            Object value,
            Map<String, Object> expectedProperties) {
        Optional<OIndex> index = propertyIndex(database, className, property);
        if (value == null || !index.isPresent()) {
            return Optional.empty();
        }
        Object indexKey = index.get().getDefinition().createValue(value);
        try (Stream<ORID> identities = index.get().getInternal().getRids(indexKey)) {
            Iterator<ORID> iterator = identities.iterator();
            while (iterator.hasNext()) {
                ORecord record = database.load(iterator.next());
                if (!(record instanceof OElement)) {
                    continue;
                }
                OElement element = (OElement) record;
                boolean matches = true;
                for (Map.Entry<String, Object> expected : expectedProperties.entrySet()) {
                    if (!Objects.equals(element.getProperty(expected.getKey()), expected.getValue())) {
                        matches = false;
                        break;
                    }
                }
                if (matches) {
                    return Optional.of(element);
                }
            }
        }
        return Optional.empty();
    }

    static Optional<OElement> findTarget(
            ODatabaseSession database,
            UpdateSpec spec,
            OElement stagingRow) {
        String firstProperty = spec.matchProperties.get(0);
        Object firstValue = stagingRow.getProperty(firstProperty);
        Map<String, Object> expectedProperties = new LinkedHashMap<>();
        for (String property : spec.matchProperties) {
            expectedProperties.put(property, stagingRow.getProperty(property));
        }
        if (firstValue != null && propertyIndex(database, spec.targetClass, firstProperty).isPresent()) {
            return findIndexedElement(
                    database,
                    spec.targetClass,
                    firstProperty,
                    firstValue,
                    expectedProperties);
        }
        StringBuilder query = new StringBuilder("SELECT FROM ")
                .append(spec.targetClass)
                .append(" WHERE ");
        List<Object> parameters = new ArrayList<>();
        for (int index = 0; index < spec.matchProperties.size(); index++) {
            if (index > 0) {
                query.append(" AND ");
            }
            String property = spec.matchProperties.get(index);
            Object value = stagingRow.getProperty(property);
            query.append(property);
            if (value == null) {
                query.append(" IS NULL");
            } else {
                query.append(" = ?");
                parameters.add(value);
            }
        }
        query.append(" LIMIT 1");
        return queryOneElement(database, query.toString(), parameters.toArray());
    }

    static String endpointCacheKey(String className, String key, Object value) {
        return className + "\u0000" + key + "\u0000" + (value == null ? "" : value.toString());
    }

    static OVertex resolveEndpoint(
            ODatabaseSession database,
            String className,
            String key,
            Object value,
            Map<String, OVertex> cache) {
        String cacheKey = endpointCacheKey(className, key, value);
        OVertex cached = cache.get(cacheKey);
        if (cached != null) {
            return cached;
        }
        Optional<OElement> endpoint;
        if (value == null) {
            endpoint = queryOneElement(
                    database,
                    "SELECT FROM " + className + " WHERE " + key + " IS NULL LIMIT 1");
        } else if (propertyIndex(database, className, key).isPresent()) {
            endpoint = findIndexedElement(
                    database,
                    className,
                    key,
                    value,
                    Collections.singletonMap(key, value));
        } else {
            endpoint = queryOneElement(
                    database,
                    "SELECT FROM " + className + " WHERE " + key + " = ? LIMIT 1",
                    value);
        }
        if (!endpoint.isPresent()) {
            endpoint = queryOneElement(
                    database,
                    "SELECT FROM _MissingEndpoint WHERE target_class = ? AND target_key = ? "
                            + "AND target_value = ? LIMIT 1",
                    className,
                    key,
                    value == null ? "" : value.toString());
        }
        OVertex vertex = endpoint
                .flatMap(OElement::asVertex)
                .orElseThrow(() -> new IllegalStateException(
                        "missing endpoint " + className + "." + key + "=" + value));
        cache.put(cacheKey, vertex);
        return vertex;
    }

    static void copyProperties(OElement source, OElement target) {
        for (String property : source.getPropertyNames()) {
            if ("out".equals(property) || "in".equals(property) || property.startsWith("@")) {
                continue;
            }
            Object value = source.getProperty(property);
            if (value != null) {
                target.setProperty(property, value);
            }
        }
    }

    static void rollbackActive(ODatabaseSession database) {
        if (database.getTransaction().isActive()) {
            database.rollback();
        }
    }

    static void commitUpdateBatch(ODatabaseSession database) {
        database.commit();
        database.getLocalCache().clear();
    }

    static void ensureUpdateSupportSchema(ODatabaseSession database) {
        rollbackActive(database);
        OClass shadowClass = database.getMetadata().getSchema().getClass(UPDATE6_AUTHOR_SHADOW);
        if (shadowClass == null) {
            shadowClass = database.createClass(UPDATE6_AUTHOR_SHADOW, "V");
        }
        if (!shadowClass.isSubClassOf("V")) {
            throw new IllegalStateException(UPDATE6_AUTHOR_SHADOW + " is not a vertex class");
        }
        if (shadowClass.getProperty("authorid") == null) {
            shadowClass.createProperty("authorid", OType.STRING);
        }
        if (shadowClass.getClassIndex(UPDATE6_AUTHOR_SHADOW_INDEX) == null) {
            shadowClass.createIndex(
                    UPDATE6_AUTHOR_SHADOW_INDEX,
                    OClass.INDEX_TYPE.UNIQUE,
                    "authorid");
        }

        OClass progressClass = database.getMetadata().getSchema().getClass(UPDATE_RECOVERY_PROGRESS);
        if (progressClass == null) {
            progressClass = database.createClass(UPDATE_RECOVERY_PROGRESS);
        }
        if (progressClass.isSubClassOf("V") || progressClass.isSubClassOf("E")) {
            throw new IllegalStateException(
                    UPDATE_RECOVERY_PROGRESS + " must be a document class");
        }
        if (progressClass.getProperty("operation") == null) {
            progressClass.createProperty("operation", OType.STRING);
        }
        if (progressClass.getProperty("target_class") == null) {
            progressClass.createProperty("target_class", OType.STRING);
        }
        if (progressClass.getProperty("staging_class") == null) {
            progressClass.createProperty("staging_class", OType.STRING);
        }
        if (progressClass.getProperty("processed_rows") == null) {
            progressClass.createProperty("processed_rows", OType.LONG);
        }
        if (progressClass.getProperty("last_rid") == null) {
            progressClass.createProperty("last_rid", OType.STRING);
        }
        if (progressClass.getProperty("completed") == null) {
            progressClass.createProperty("completed", OType.BOOLEAN);
        }
        if (progressClass.getClassIndex(UPDATE_RECOVERY_PROGRESS_INDEX) == null) {
            progressClass.createIndex(
                    UPDATE_RECOVERY_PROGRESS_INDEX,
                    OClass.INDEX_TYPE.UNIQUE,
                    "operation",
                    "target_class",
                    "staging_class");
        }
    }

    static Optional<OVertex> findVertex(
            ODatabaseSession database,
            String className,
            String property,
            Object value) {
        Optional<OElement> element;
        if (value == null) {
            element = queryOneElement(
                    database,
                    "SELECT FROM " + className + " WHERE " + property + " IS NULL LIMIT 1");
        } else {
            element = queryOneElement(
                    database,
                    "SELECT FROM " + className + " WHERE " + property + " = ? LIMIT 1",
                    value);
        }
        return element.flatMap(OElement::asVertex);
    }

    static UpdateExecutionResult moveAuthors(
            ODatabaseSession database,
            String fromClass,
            String toClass,
            int batchSize,
            boolean allowMissing) {
        UpdateExecutionResult result = new UpdateExecutionResult();
        int pending = 0;
        database.begin();
        try (OResultSet stagingRows = database.query(
                "SELECT FROM grbench_update4_authors_gender")) {
            while (stagingRows.hasNext()) {
                OResult stagingResult = stagingRows.next();
                if (!stagingResult.isElement()) {
                    throw new IllegalStateException(
                            "staging row is not an element: grbench_update4_authors_gender");
                }
                OElement stagingRow = stagingResult.toElement();
                Object authorId = stagingRow.getProperty("authorid");
                result.visitedRows++;
                Optional<OVertex> source = findVertex(database, fromClass, "authorid", authorId);
                if (!source.isPresent()) {
                    result.missingRows++;
                    if (!allowMissing) {
                        throw new IllegalStateException(
                                "author vertex missing from " + fromClass + ": " + authorId);
                    }
                    continue;
                }
                if (findVertex(database, toClass, "authorid", authorId).isPresent()) {
                    throw new IllegalStateException(
                            "author vertex exists in both " + fromClass + " and " + toClass
                                    + ": " + authorId);
                }
                source.get().moveTo(toClass, null);
                result.modifiedRows++;
                pending++;
                if (pending >= batchSize) {
                    commitUpdateBatch(database);
                    result.committedBatches++;
                    database.begin();
                    pending = 0;
                }
            }
            if (pending > 0) {
                commitUpdateBatch(database);
                result.committedBatches++;
            } else {
                rollbackActive(database);
            }
            return result;
        } catch (Throwable throwable) {
            rollbackActive(database);
            throw throwable;
        }
    }

    static UpdateExecutionResult deleteSpec(
            ODatabaseSession database,
            UpdateSpec spec,
            int batchSize,
            boolean allowMissing) {
        UpdateExecutionResult result = new UpdateExecutionResult();
        int pending = 0;
        database.begin();
        try (OResultSet stagingRows = database.query("SELECT FROM " + spec.stagingClass)) {
            while (stagingRows.hasNext()) {
                OResult stagingResult = stagingRows.next();
                if (!stagingResult.isElement()) {
                    throw new IllegalStateException("staging row is not an element: " + spec.stagingClass);
                }
                OElement stagingRow = stagingResult.toElement();
                result.visitedRows++;
                Optional<OElement> target = findTarget(database, spec, stagingRow);
                if (!target.isPresent()) {
                    result.missingRows++;
                    if (!allowMissing) {
                        throw new IllegalStateException(
                                "target row missing for " + spec.targetClass + " from " + spec.stagingClass);
                    }
                    continue;
                }
                target.get().delete();
                result.modifiedRows++;
                pending++;
                if (pending >= batchSize) {
                    commitUpdateBatch(database);
                    result.committedBatches++;
                    database.begin();
                    pending = 0;
                }
            }
            if (pending > 0) {
                commitUpdateBatch(database);
                result.committedBatches++;
            } else {
                rollbackActive(database);
            }
            return result;
        } catch (Throwable throwable) {
            rollbackActive(database);
            throw throwable;
        }
    }

    static UpdateExecutionResult restoreSpec(
            ODatabaseSession database,
            UpdateSpec spec,
            int batchSize) {
        UpdateExecutionResult result = new UpdateExecutionResult();
        int pending = 0;
        Map<String, OVertex> endpointCache = new HashMap<>();
        database.begin();
        try (OResultSet stagingRows = database.query("SELECT FROM " + spec.stagingClass)) {
            while (stagingRows.hasNext()) {
                OResult stagingResult = stagingRows.next();
                if (!stagingResult.isElement()) {
                    throw new IllegalStateException("staging row is not an element: " + spec.stagingClass);
                }
                OElement stagingRow = stagingResult.toElement();
                result.visitedRows++;
                OElement target;
                if (spec.isEdge()) {
                    OVertex from = resolveEndpoint(
                            database,
                            spec.fromClass,
                            spec.fromKey,
                            stagingRow.getProperty(spec.fromValueProperty),
                            endpointCache);
                    OVertex to = resolveEndpoint(
                            database,
                            spec.toClass,
                            spec.toKey,
                            stagingRow.getProperty(spec.toValueProperty),
                            endpointCache);
                    target = database.newEdge(from, to, spec.targetClass);
                } else {
                    target = database.newVertex(spec.targetClass);
                }
                copyProperties(stagingRow, target);
                target.save();
                result.modifiedRows++;
                pending++;
                if (pending >= batchSize) {
                    commitUpdateBatch(database);
                    result.committedBatches++;
                    database.begin();
                    endpointCache.clear();
                    pending = 0;
                }
            }
            if (pending > 0) {
                commitUpdateBatch(database);
                result.committedBatches++;
            } else {
                rollbackActive(database);
            }
            return result;
        } catch (Throwable throwable) {
            rollbackActive(database);
            throw throwable;
        }
    }

    static String recoveryOperation(String filename) {
        return restoreFilename(filename);
    }

    static Optional<OElement> findRecoveryProgress(
            ODatabaseSession database,
            String operation,
            UpdateSpec spec) {
        return queryOneElement(
                database,
                "SELECT FROM " + UPDATE_RECOVERY_PROGRESS
                        + " WHERE operation = ? AND target_class = ? AND staging_class = ? LIMIT 1",
                operation,
                spec.targetClass,
                spec.stagingClass);
    }

    static long progressLong(OElement progress, String property) {
        Object value = progress.getProperty(property);
        if (value instanceof Number) {
            return ((Number) value).longValue();
        }
        if (value == null) {
            return 0L;
        }
        return Long.parseLong(value.toString());
    }

    static boolean progressBoolean(OElement progress, String property) {
        Object value = progress.getProperty(property);
        if (value instanceof Boolean) {
            return (Boolean) value;
        }
        return value != null && Boolean.parseBoolean(value.toString());
    }

    static OElement newRecoveryProgress(
            ODatabaseSession database,
            String operation,
            UpdateSpec spec) {
        OElement progress = database.newElement(UPDATE_RECOVERY_PROGRESS);
        progress.setProperty("operation", operation);
        progress.setProperty("target_class", spec.targetClass);
        progress.setProperty("staging_class", spec.stagingClass);
        progress.setProperty("processed_rows", 0L);
        progress.setProperty("completed", false);
        return progress;
    }

    static List<OElement> readRecoveryBatch(
            ODatabaseSession database,
            UpdateSpec spec,
            long processedRows,
            String lastRid,
            int batchSize) {
        OClass stagingClass = database.getMetadata().getSchema().getClass(spec.stagingClass);
        if (stagingClass == null) {
            throw new IllegalStateException("missing recovery staging class: " + spec.stagingClass);
        }
        int[] clusterIds = stagingClass.getPolymorphicClusterIds();
        Arrays.sort(clusterIds);

        ORecordId lastRecordId = null;
        if (lastRid != null && !lastRid.isEmpty()) {
            lastRecordId = new ORecordId(lastRid);
            if (!lastRecordId.isPersistent()) {
                throw new IllegalStateException(
                        "invalid recovery last_rid for " + spec.stagingClass + ": " + lastRid);
            }
        }

        List<OElement> rows = new ArrayList<>(batchSize + 1);
        long rowsToSkip = lastRecordId == null ? processedRows : 0L;
        boolean cursorClusterFound = lastRecordId == null;
        for (int clusterId : clusterIds) {
            if (lastRecordId != null && clusterId < lastRecordId.getClusterId()) {
                continue;
            }
            if (lastRecordId != null && clusterId == lastRecordId.getClusterId()) {
                cursorClusterFound = true;
            }
            long startPosition = lastRecordId != null && clusterId == lastRecordId.getClusterId()
                    ? lastRecordId.getClusterPosition() + 1L
                    : 0L;
            String clusterName = database.getClusterNameById(clusterId);
            Iterator<ORecord> stagingRows = database.browseCluster(
                    clusterName,
                    ORecord.class,
                    startPosition,
                    Long.MAX_VALUE,
                    false);
            while (stagingRows.hasNext()) {
                ORecord stagingRecord = stagingRows.next();
                if (rowsToSkip > 0) {
                    rowsToSkip--;
                    continue;
                }
                if (!(stagingRecord instanceof OElement)) {
                    throw new IllegalStateException(
                            "staging row is not an element: " + spec.stagingClass);
                }
                rows.add((OElement) stagingRecord);
                if (rows.size() > batchSize) {
                    return rows;
                }
            }
        }
        if (!cursorClusterFound) {
            throw new IllegalStateException(
                    "recovery last_rid cluster is outside staging class "
                            + spec.stagingClass + ": " + lastRid);
        }
        if (rowsToSkip > 0) {
            throw new IllegalStateException(
                    "recovery processed_rows exceeds staging class size for "
                            + spec.stagingClass + ": " + processedRows);
        }
        return rows;
    }

    static UpdateExecutionResult restoreSpecResumable(
            ODatabaseSession database,
            String operation,
            UpdateSpec spec,
            int batchSize) {
        UpdateExecutionResult result = new UpdateExecutionResult();
        while (true) {
            database.begin();
            try {
                Optional<OElement> existingProgress = findRecoveryProgress(
                        database,
                        operation,
                        spec);
                OElement progress = existingProgress.orElseGet(
                        () -> newRecoveryProgress(database, operation, spec));
                long processedRows = progressLong(progress, "processed_rows");
                if (processedRows < 0) {
                    throw new IllegalStateException(
                            "negative recovery progress for " + spec.stagingClass);
                }
                if (progressBoolean(progress, "completed")) {
                    rollbackActive(database);
                    return result;
                }
                String lastRid = progress.getProperty("last_rid");
                List<OElement> rows = readRecoveryBatch(
                        database,
                        spec,
                        processedRows,
                        lastRid,
                        batchSize);
                int rowsToRestore = Math.min(rows.size(), batchSize);
                boolean completed = rows.size() <= batchSize;
                Map<String, OVertex> endpointCache = new HashMap<>();
                String newLastRid = lastRid;
                for (int index = 0; index < rowsToRestore; index++) {
                    OElement stagingRow = rows.get(index);
                    result.visitedRows++;
                    OElement target;
                    if (spec.isEdge()) {
                        OVertex from = resolveEndpoint(
                                database,
                                spec.fromClass,
                                spec.fromKey,
                                stagingRow.getProperty(spec.fromValueProperty),
                                endpointCache);
                        OVertex to = resolveEndpoint(
                                database,
                                spec.toClass,
                                spec.toKey,
                                stagingRow.getProperty(spec.toValueProperty),
                                endpointCache);
                        target = database.newEdge(from, to, spec.targetClass);
                    } else {
                        target = database.newVertex(spec.targetClass);
                    }
                    copyProperties(stagingRow, target);
                    target.save();
                    result.modifiedRows++;
                    ORID identity = stagingRow.getIdentity();
                    if (!identity.isPersistent()) {
                        throw new IllegalStateException(
                                "staging row has no persistent RID: " + spec.stagingClass);
                    }
                    newLastRid = identity.toString();
                }

                progress.setProperty(
                        "processed_rows",
                        Math.addExact(processedRows, (long) rowsToRestore));
                if (newLastRid != null && !newLastRid.isEmpty()) {
                    progress.setProperty("last_rid", newLastRid);
                }
                progress.setProperty("completed", completed);
                progress.save();
                commitUpdateBatch(database);
                result.committedBatches++;
                if (completed) {
                    return result;
                }
            } catch (Throwable throwable) {
                rollbackActive(database);
                throw throwable;
            }
        }
    }

    static UpdateExecutionResult clearRecoveryProgress(
            ODatabaseSession database,
            String operation) {
        UpdateExecutionResult result = new UpdateExecutionResult();
        database.begin();
        try (OResultSet rows = database.query(
                "SELECT FROM " + UPDATE_RECOVERY_PROGRESS + " WHERE operation = ?",
                operation)) {
            while (rows.hasNext()) {
                OResult row = rows.next();
                if (!row.isElement()) {
                    throw new IllegalStateException(
                            "recovery progress row is not an element: " + operation);
                }
                result.visitedRows++;
                row.toElement().delete();
                result.modifiedRows++;
            }
            if (result.modifiedRows > 0) {
                commitUpdateBatch(database);
                result.committedBatches++;
            } else {
                rollbackActive(database);
            }
            return result;
        } catch (Throwable throwable) {
            rollbackActive(database);
            throw throwable;
        }
    }

    static ExecutionResult updateResultToExecutionResult(UpdateExecutionResult updateResult) {
        ExecutionResult executionResult = new ExecutionResult();
        MaterializedResultSet resultSet = new MaterializedResultSet();
        resultSet.columns.add("benchmark_value");
        resultSet.columns.add("visited_rows");
        resultSet.columns.add("missing_rows");
        resultSet.columns.add("committed_batches");
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("benchmark_value", updateResult.modifiedRows);
        row.put("visited_rows", updateResult.visitedRows);
        row.put("missing_rows", updateResult.missingRows);
        row.put("committed_batches", updateResult.committedBatches);
        resultSet.rows.add(row);
        executionResult.resultSets.add(resultSet);
        executionResult.rowCount = 1;
        return executionResult;
    }

    static void restoreUpdateStrict(
            ODatabaseSession database,
            String filename,
            int batchSize,
            UpdateExecutionResult result) {
        String restoreFile = restoreFilename(filename);
        if ("U6b.sql".equals(restoreFile)) {
            result.add(moveAuthors(
                    database,
                    UPDATE6_AUTHOR_SHADOW,
                    "Authors_Gender",
                    batchSize,
                    false));
        }
        for (UpdateSpec spec : restoreSpecs(restoreFile)) {
            result.add(restoreSpec(database, spec, batchSize));
        }
    }

    static void restoreUpdateResumable(
            ODatabaseSession database,
            String filename,
            int batchSize,
            UpdateExecutionResult result) {
        String restoreFile = restoreFilename(filename);
        String operation = recoveryOperation(filename);
        if ("U6b.sql".equals(restoreFile)) {
            result.add(moveAuthors(
                    database,
                    UPDATE6_AUTHOR_SHADOW,
                    "Authors_Gender",
                    batchSize,
                    true));
        }
        for (UpdateSpec spec : restoreSpecs(restoreFile)) {
            result.add(restoreSpecResumable(database, operation, spec, batchSize));
        }
    }

    static ExecutionResult executeUpdate(
            ODatabaseSession database,
            String filename,
            int batchSize,
            String mode) {
        if (batchSize < 1) {
            throw new IllegalArgumentException("Update batch size must be >= 1");
        }
        boolean retainRecords = database.isRetainRecords();
        database.setRetainRecords(false);
        try {
            UpdateExecutionResult result = new UpdateExecutionResult();
            if ("STRICT".equals(mode)) {
                List<UpdateSpec> specs = filename.endsWith("a.sql")
                        ? deleteSpecs(filename)
                        : restoreSpecs(filename);
                if (filename.endsWith("a.sql")) {
                    for (UpdateSpec spec : specs) {
                        result.add(deleteSpec(database, spec, batchSize, false));
                    }
                    if ("U6a.sql".equals(filename)) {
                        result.add(moveAuthors(
                                database,
                                "Authors_Gender",
                                UPDATE6_AUTHOR_SHADOW,
                                batchSize,
                                false));
                    }
                } else {
                    restoreUpdateStrict(database, filename, batchSize, result);
                }
            } else if ("RECOVER".equals(mode)) {
                clearRecoveryProgress(database, recoveryOperation(filename));
                for (UpdateSpec spec : deleteSpecs(deleteFilename(filename))) {
                    result.add(deleteSpec(database, spec, batchSize, true));
                }
                if ("U6a.sql".equals(deleteFilename(filename))) {
                    result.add(moveAuthors(
                            database,
                            "Authors_Gender",
                            UPDATE6_AUTHOR_SHADOW,
                            batchSize,
                            true));
                    result.add(moveAuthors(
                            database,
                            UPDATE6_AUTHOR_SHADOW,
                            "Authors_Gender",
                            batchSize,
                            false));
                }
                restoreUpdateResumable(database, filename, batchSize, result);
            } else if ("RESTORE_ONLY".equals(mode)) {
                restoreUpdateResumable(database, filename, batchSize, result);
            } else if ("FINALIZE_RECOVERY".equals(mode)) {
                result.add(clearRecoveryProgress(database, recoveryOperation(filename)));
            } else {
                throw new IllegalArgumentException("unsupported Update mode: " + mode);
            }
            return updateResultToExecutionResult(result);
        } finally {
            rollbackActive(database);
            database.setRetainRecords(retainRecords);
        }
    }

    static Args parseArgs(String[] argv) {
        Args args = new Args();
        for (int index = 0; index < argv.length; index++) {
            String argument = argv[index];
            if ("--db-root".equals(argument)) {
                args.dbRoot = argv[++index];
            } else if ("--database".equals(argument)) {
                args.database = argv[++index];
            } else if ("--max-result-rows".equals(argument)) {
                args.maxResultRows = Integer.parseInt(argv[++index]);
            } else {
                throw new IllegalArgumentException("unknown argument: " + argument);
            }
        }
        if (args.dbRoot == null || args.database == null) {
            throw new IllegalArgumentException("--db-root and --database are required");
        }
        if (args.maxResultRows < 1) {
            throw new IllegalArgumentException("--max-result-rows must be >= 1");
        }
        return args;
    }

    static String decode(String encoded) {
        return new String(Base64.getDecoder().decode(encoded), StandardCharsets.UTF_8);
    }

    static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }

    static String stripScriptWrapper(String statement) {
        String normalized = statement.replace("\r\n", "\n").replace('\r', '\n').trim();
        int firstNewline = normalized.indexOf('\n');
        if (firstNewline < 0) {
            throw new IllegalArgumentException("OrientDB SQL script has no body");
        }
        String body = normalized.substring(firstNewline + 1).trim();
        String lower = body.toLowerCase(Locale.ROOT);
        if (lower.endsWith("\nend;")) {
            body = body.substring(0, body.length() - 5).trim();
        } else if (lower.endsWith("\nend")) {
            body = body.substring(0, body.length() - 4).trim();
        }
        return body;
    }

    static OResultSet executeStatement(ODatabaseSession database, String statement) {
        String trimmed = statement.trim();
        String lower = trimmed.toLowerCase(Locale.ROOT);
        if ("begin".equals(lower) || "begin transaction".equals(lower)) {
            database.begin();
            return null;
        }
        if ("rollback".equals(lower)) {
            if (database.getTransaction().isActive()) {
                database.rollback();
            }
            return null;
        }
        if ("commit".equals(lower)) {
            if (database.getTransaction().isActive()) {
                database.commit();
            }
            return null;
        }
        if (lower.startsWith("script ")) {
            return database.execute("sql", stripScriptWrapper(trimmed));
        }
        if (lower.startsWith("select ")
                || lower.startsWith("match ")
                || lower.startsWith("traverse ")
                || lower.startsWith("explain ")
                || lower.startsWith("profile ")) {
            return database.query(trimmed);
        }
        return database.command(trimmed);
    }

    static void consume(
            OResultSet orientResultSet,
            ExecutionResult executionResult,
            int maxResultRows) {
        if (orientResultSet == null) {
            return;
        }
        MaterializedResultSet materialized = new MaterializedResultSet();
        try (OResultSet resultSet = orientResultSet) {
            while (resultSet.hasNext()) {
                if (executionResult.rowCount >= maxResultRows) {
                    throw new IllegalStateException(
                            "result row limit exceeded: " + maxResultRows + "; no truncation was performed");
                }
                OResult result = resultSet.next();
                Map<String, Object> row = new LinkedHashMap<>();
                for (String property : result.getPropertyNames()) {
                    materialized.columns.add(property);
                    row.put(property, result.getProperty(property));
                }
                if (row.isEmpty() && result.isElement()) {
                    row.put("@rid", result.getIdentity().map(Object::toString).orElse(null));
                    materialized.columns.add("@rid");
                }
                materialized.rows.add(row);
                executionResult.rowCount++;
            }
        }
        executionResult.resultSets.add(materialized);
    }

    static ExecutionResult execute(
            ODatabaseSession database,
            List<String> statements,
            int maxResultRows) {
        ExecutionResult result = new ExecutionResult();
        for (String statement : statements) {
            consume(executeStatement(database, statement), result, maxResultRows);
        }
        return result;
    }

    static String quoteJson(String value) {
        StringBuilder output = new StringBuilder(value.length() + 16);
        output.append('"');
        for (int index = 0; index < value.length(); index++) {
            char character = value.charAt(index);
            switch (character) {
                case '"':
                    output.append("\\\"");
                    break;
                case '\\':
                    output.append("\\\\");
                    break;
                case '\b':
                    output.append("\\b");
                    break;
                case '\f':
                    output.append("\\f");
                    break;
                case '\n':
                    output.append("\\n");
                    break;
                case '\r':
                    output.append("\\r");
                    break;
                case '\t':
                    output.append("\\t");
                    break;
                default:
                    if (character < 0x20) {
                        output.append(String.format("\\u%04x", (int) character));
                    } else {
                        output.append(character);
                    }
            }
        }
        output.append('"');
        return output.toString();
    }

    static String numberToJson(Number value) {
        if (value instanceof BigDecimal) {
            return ((BigDecimal) value).toPlainString();
        }
        if (value instanceof BigInteger) {
            return value.toString();
        }
        if (value instanceof Double) {
            double number = value.doubleValue();
            return Double.isFinite(number) ? Double.toString(number) : quoteJson(Double.toString(number));
        }
        if (value instanceof Float) {
            float number = value.floatValue();
            return Float.isFinite(number) ? Float.toString(number) : quoteJson(Float.toString(number));
        }
        return value.toString();
    }

    static String valueToJson(Object value, int depth) {
        if (value == null) {
            return "null";
        }
        if (depth > 12) {
            return quoteJson("<MAX_DEPTH>");
        }
        if (value instanceof String || value instanceof Character || value instanceof Enum<?>) {
            return quoteJson(value.toString());
        }
        if (value instanceof Boolean) {
            return value.toString();
        }
        if (value instanceof Number) {
            return numberToJson((Number) value);
        }
        if (value instanceof Date) {
            return quoteJson(((Date) value).toInstant().toString());
        }
        if (value instanceof Instant) {
            return quoteJson(value.toString());
        }
        if (value instanceof byte[]) {
            return quoteJson(Base64.getEncoder().encodeToString((byte[]) value));
        }
        if (value instanceof ORID) {
            return quoteJson(value.toString());
        }
        if (value instanceof OIdentifiable) {
            return quoteJson(((OIdentifiable) value).getIdentity().toString());
        }
        if (value instanceof OResult) {
            OResult result = (OResult) value;
            Map<String, Object> properties = new LinkedHashMap<>();
            for (String property : result.getPropertyNames()) {
                properties.put(property, result.getProperty(property));
            }
            return mapToJson(properties, depth + 1);
        }
        if (value instanceof OElement) {
            OElement element = (OElement) value;
            ORID identity = element.getIdentity();
            return quoteJson(identity == null ? element.toString() : identity.toString());
        }
        if (value instanceof Map<?, ?>) {
            return mapToJson((Map<?, ?>) value, depth + 1);
        }
        if (value instanceof Iterable<?>) {
            return iterableToJson(((Iterable<?>) value).iterator(), depth + 1);
        }
        if (value instanceof Iterator<?>) {
            return iterableToJson((Iterator<?>) value, depth + 1);
        }
        if (value.getClass().isArray()) {
            StringBuilder output = new StringBuilder("[");
            int length = Array.getLength(value);
            for (int index = 0; index < length; index++) {
                if (index > 0) {
                    output.append(',');
                }
                output.append(valueToJson(Array.get(value, index), depth + 1));
            }
            return output.append(']').toString();
        }
        return quoteJson(value.toString());
    }

    static String iterableToJson(Iterator<?> values, int depth) {
        StringBuilder output = new StringBuilder("[");
        boolean first = true;
        while (values.hasNext()) {
            if (!first) {
                output.append(',');
            }
            output.append(valueToJson(values.next(), depth + 1));
            first = false;
        }
        return output.append(']').toString();
    }

    static String mapToJson(Map<?, ?> values, int depth) {
        List<Map.Entry<String, Object>> entries = new ArrayList<>();
        for (Map.Entry<?, ?> entry : values.entrySet()) {
            entries.add(new java.util.AbstractMap.SimpleImmutableEntry<>(
                    String.valueOf(entry.getKey()),
                    entry.getValue()));
        }
        Collections.sort(entries, (left, right) -> left.getKey().compareTo(right.getKey()));
        StringBuilder output = new StringBuilder("{");
        for (int index = 0; index < entries.size(); index++) {
            Map.Entry<String, Object> entry = entries.get(index);
            if (index > 0) {
                output.append(',');
            }
            output.append(quoteJson(entry.getKey()))
                    .append(':')
                    .append(valueToJson(entry.getValue(), depth + 1));
        }
        return output.append('}').toString();
    }

    static String resultToJson(ExecutionResult result) {
        StringBuilder output = new StringBuilder("{\"result_sets\":[");
        for (int setIndex = 0; setIndex < result.resultSets.size(); setIndex++) {
            if (setIndex > 0) {
                output.append(',');
            }
            MaterializedResultSet resultSet = result.resultSets.get(setIndex);
            List<String> columns = new ArrayList<>(resultSet.columns);
            output.append("{\"columns\":[");
            for (int columnIndex = 0; columnIndex < columns.size(); columnIndex++) {
                if (columnIndex > 0) {
                    output.append(',');
                }
                output.append(quoteJson(columns.get(columnIndex)));
            }
            output.append("],\"rows\":[");
            for (int rowIndex = 0; rowIndex < resultSet.rows.size(); rowIndex++) {
                if (rowIndex > 0) {
                    output.append(',');
                }
                Map<String, Object> row = resultSet.rows.get(rowIndex);
                output.append('[');
                for (int columnIndex = 0; columnIndex < columns.size(); columnIndex++) {
                    if (columnIndex > 0) {
                        output.append(',');
                    }
                    output.append(valueToJson(row.get(columns.get(columnIndex)), 0));
                }
                output.append(']');
            }
            output.append("]}");
        }
        output.append("],\"result_row_count\":").append(result.rowCount).append('}');
        return output.toString();
    }

    static String stackTrace(Throwable throwable) {
        StringWriter buffer = new StringWriter();
        throwable.printStackTrace(new PrintWriter(buffer));
        return buffer.toString();
    }

    static long processCpuTime() {
        long value = OPERATING_SYSTEM.getProcessCpuTime();
        return Math.max(0L, value);
    }

    static void send(PrintWriter output, String message) {
        output.println(message);
        output.flush();
    }

    static void runLoop(ODatabaseSession database, Args args) throws Exception {
        BufferedReader input = new BufferedReader(
                new InputStreamReader(System.in, StandardCharsets.UTF_8));
        PrintWriter output = new PrintWriter(System.out, false, StandardCharsets.UTF_8);
        send(output, READY + "\t" + PROTOCOL_VERSION);
        String line;
        while ((line = input.readLine()) != null) {
            if (CLOSE.equals(line)) {
                return;
            }
            String[] fields = line.split("\\t", -1);
            if (fields.length < 3 || (!EXEC.equals(fields[0]) && !UPDATE.equals(fields[0]))) {
                send(output, RESULT + "\tUNKNOWN\tERROR\t0\t0\t"
                        + encode("invalid protocol request"));
                continue;
            }
            String requestId = fields[1];
            long started = 0L;
            long cpuStarted = 0L;
            try {
                send(output, START + "\t" + requestId);
                started = System.nanoTime();
                cpuStarted = processCpuTime();
                ExecutionResult result;
                if (EXEC.equals(fields[0])) {
                    int statementCount = Integer.parseInt(fields[2]);
                    if (statementCount < 1 || fields.length != statementCount + 3) {
                        throw new IllegalArgumentException("statement count does not match protocol fields");
                    }
                    List<String> statements = new ArrayList<>();
                    for (int index = 0; index < statementCount; index++) {
                        statements.add(decode(fields[index + 3]));
                    }
                    result = execute(database, statements, args.maxResultRows);
                } else {
                    if (fields.length != 5) {
                        throw new IllegalArgumentException("invalid native Update protocol request");
                    }
                    result = executeUpdate(
                            database,
                            fields[2],
                            Integer.parseInt(fields[3]),
                            fields[4]);
                }
                long elapsed = System.nanoTime() - started;
                long cpuElapsed = Math.max(0L, processCpuTime() - cpuStarted);
                send(output, RESULT + "\t" + requestId + "\tOK\t" + elapsed + "\t"
                        + cpuElapsed + "\t"
                        + encode(resultToJson(result)));
            } catch (Throwable throwable) {
                long elapsed = started == 0L ? 0L : System.nanoTime() - started;
                long cpuElapsed = cpuStarted == 0L ? 0L : Math.max(0L, processCpuTime() - cpuStarted);
                send(output, RESULT + "\t" + requestId + "\tERROR\t" + elapsed + "\t"
                        + cpuElapsed + "\t"
                        + encode(stackTrace(throwable)));
            }
        }
    }

    public static void main(String[] argv) throws Exception {
        Args args = parseArgs(argv);
        try (OrientDB orient = new OrientDB(
                "embedded:" + args.dbRoot,
                OrientDBConfig.defaultConfig());
             ODatabaseSession database = orient.open(
                     args.database,
                     requireEnvironment("ORIENTDB_USERNAME"),
                     requireEnvironment("ORIENTDB_PASSWORD"))) {
            ensureUpdateSupportSchema(database);
            runLoop(database, args);
        }
    }
}
