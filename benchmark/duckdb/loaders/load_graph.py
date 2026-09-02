import argparse
import duckdb
import os
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
parser = argparse.ArgumentParser(description="Load canonical SciSciNet CSVs into DuckDB/DuckPGQ.")
parser.add_argument("--sf", choices=[f"sf10_{i}" for i in range(5)], default="sf10_2")
parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("GRBENCH_DATA_ROOT", REPO_ROOT / "data" / "processed")))
parser.add_argument("--db", type=Path, default=None)
parser.add_argument("--threads", type=int, default=int(os.environ.get("GRBENCH_THREADS", "8")))
parser.add_argument("--memory-limit", default="64GB")
args = parser.parse_args()

DB_FILE = args.db or REPO_ROOT / ".local" / "duckdb" / f"sciscinet_graph_{args.sf.removeprefix('sf10_')}.duckdb"
DATA_DIR = args.data_root / args.sf
DB_FILE.parent.mkdir(parents=True, exist_ok=True)
con = duckdb.connect(str(DB_FILE), config={'allow_unsigned_extensions':'true'})
con.execute(f"SET memory_limit='{args.memory_limit}';")
con.execute(f"PRAGMA threads={args.threads};")
con.execute("INSTALL duckpgq FROM community;")
con.execute("LOAD duckpgq;")
print("DuckPGQ loaded OK")
def sample_csv(file_name):
    return str(DATA_DIR / file_name)
papers_csv= sample_csv("sciscinet_papers.csv")
authors_csv = sample_csv("sciscinet_authors.csv")
author_details_csv = sample_csv("sciscinet_author_details.csv")
affiliations_csv = sample_csv("sciscinet_affiliations.csv")
sources_csv = sample_csv("sciscinet_sources.csv")
papersources_csv = sample_csv("sciscinet_papersources.csv")
paperdetails_csv = sample_csv("sciscinet_paperdetails.csv")
fields_csv = sample_csv("sciscinet_fields.csv")
hit_papers_level1_csv = sample_csv("hit_papers_level1.csv")
nsf_csv = sample_csv("sciscinet_nsf_metadata.csv")
link_nsf_csv = sample_csv("sciscinet_link_nsf.csv")
nih_csv = sample_csv("sciscinet_nih_metadata.csv")
link_nih_csv = sample_csv("sciscinet_link_nih.csv")
clinicaltrials_csv = sample_csv("sciscinet_clinicaltrials_metadata.csv")
link_clinicaltrials_csv = sample_csv("sciscinet_link_clinicaltrials.csv")
newsfeed_csv = sample_csv("sciscinet_newsfeed_metadata.csv")
link_newsfeed_csv = sample_csv("sciscinet_link_newsfeed.csv")
hit_papers_level0_csv = sample_csv("hit_papers_level0.csv")
link_nobellaureates_csv = sample_csv("sciscinet_link_nobellaureates.csv")
link_patents_csv = sample_csv("sciscinet_link_patents.csv")
paper_author_aff_csv = sample_csv("sciscinet_author_affiliation.csv")
affl_assoc_affl_csv = sample_csv("sciscinet_affl_assoc_affl.csv")
paper_author_csv = sample_csv("sciscinet_authors_paperid.csv")
paperfields_csv = sample_csv("sciscinet_paperfields.csv")
paperrefs_csv = sample_csv("sciscinet_paperrefs.csv")
twitter_csv = sample_csv("sciscinet_twitter_metadata.csv")
link_twitter_csv = sample_csv("sciscinet_link_twitter.csv")
normalized_citations_level0_csv = sample_csv("normalized_citations_level0.csv")
normalized_citations_level1_csv = sample_csv("normalized_citations_level1.csv")
def log_vertex_count(con, table_name):
    cnt = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    print(f"[VERTEX] {table_name}: {cnt} nodes")


# -------------------------------
# 安全 CSV 读取工具（统一）
# -------------------------------
def csv_safe(path):
    return f"""
        read_csv_auto(
            '{path}',
            header=true,
            strict_mode=false,
            ignore_errors=true
        )
    """
def csv_safe_0(path):
    return f"""
        read_csv_auto(
            '{path}',
            header=true,
            strict_mode=false
        )
    """
def csv_safe_2(path):
    return f"""
        read_csv_auto(
            '{path}',
            header=true,
            strict_mode=false,
            nullstr='',
            sample_size=-1,
            types={{
                'year': 'VARCHAR',
                'date':'VARCHAR'
            }}
        )
    """



def csv_safe_fixed(path, columns, header=True):
    cols_array = "[" + ", ".join([f"'{c}'" for c in columns]) + "]"
    return f"""
        read_csv_auto(
            '{path}',
            header={str(header).lower()},
            column_names={cols_array},
            delim=',',
            quote='"',
            escape='"',
            nullstr='',
            encoding='UTF-8',
            strict_mode=true
        )
    """
def csv_safe_1(path):
    return f"""
        read_csv_auto(
            '{path}',
            header=true,
            strict_mode=false,
            all_varchar=true,
            ignore_errors=true
        )
    """


con.execute(f"""
CREATE OR REPLACE TABLE Papers AS
SELECT * FROM {csv_safe_2(papers_csv)};
""")

# -------------------------------
# 基础表
# -------------------------------
log_vertex_count(con, "Papers")
con.execute(f"CREATE OR REPLACE TABLE Authors_Gender AS SELECT * FROM {csv_safe_0(authors_csv)};")
log_vertex_count(con, "Authors_Gender")

con.execute(f"""
CREATE OR REPLACE TABLE author_details AS
SELECT
    column0 AS authorid,
    column1 AS orcid,
    column2 AS display_name,
    column3 AS display_name_alternatives,
    column4 AS works_count,
    column5 AS cited_by_count,
    column6 AS last_known_institution,
    column7 AS works_api_url,
    column8 AS updated_date
FROM read_csv_auto('{author_details_csv}', header=false);
""")
con.execute(f"CREATE OR REPLACE TABLE Affiliations AS SELECT * FROM {csv_safe_0(affiliations_csv)};")
log_vertex_count(con, "Affiliations")
con.execute(f"CREATE OR REPLACE TABLE sources AS SELECT * FROM {csv_safe_0(sources_csv)};")
log_vertex_count(con, "sources")
con.execute(f"CREATE OR REPLACE TABLE papersources AS SELECT * FROM {csv_safe_0(papersources_csv)};")
log_vertex_count(con, "papersources")
paperdetails_columns = [
    "paperid", "doi", "title", "display_name", "year", "date", "doctype",
    "cited_by_count", "is_retracted", "is_paratext", "cited_by_api_url",
    "abstract_inverted_index", "language"
]
con.execute(f"""
CREATE OR REPLACE TABLE PaperDetails AS
SELECT * FROM {csv_safe_fixed(paperdetails_csv, paperdetails_columns)};
""")
log_vertex_count(con, "PaperDetails")
con.execute(f"CREATE OR REPLACE TABLE Fields AS SELECT * FROM {csv_safe_0(fields_csv)};")
log_vertex_count(con, "Fields")
con.execute(f"CREATE OR REPLACE TABLE hit_papers_level1 AS SELECT * FROM {csv_safe_0(hit_papers_level1_csv)};")
log_vertex_count(con, "hit_papers_level1")
con.execute(f"CREATE OR REPLACE TABLE NSF_Metadata AS SELECT * FROM {csv_safe_0(nsf_csv)};")
log_vertex_count(con, "NSF_Metadata")
con.execute(f"CREATE OR REPLACE TABLE NIH_Metadata AS SELECT * FROM {csv_safe(nih_csv)};")
log_vertex_count(con, "NIH_Metadata")
con.execute(f"CREATE OR REPLACE TABLE clinicaltrials_metadata AS SELECT * FROM {csv_safe(clinicaltrials_csv)};")
log_vertex_count(con, "clinicaltrials_metadata")
con.execute(f"CREATE OR REPLACE TABLE Newsfeed_Metadata AS SELECT * FROM {csv_safe(newsfeed_csv)};")
log_vertex_count(con, "Newsfeed_Metadata")
con.execute(f"CREATE OR REPLACE TABLE Twitter_Metadata AS SELECT * FROM {csv_safe(twitter_csv)};")
log_vertex_count(con, "Twitter_Metadata")
con.execute(f"CREATE OR REPLACE TABLE hit_papers_level0 AS SELECT * FROM {csv_safe(hit_papers_level0_csv)};")
log_vertex_count(con, "hit_papers_level0")
con.execute(f"CREATE OR REPLACE TABLE normalized_citations_level0 AS SELECT * FROM {csv_safe(normalized_citations_level0_csv)};")
log_vertex_count(con, "normalized_citations_level0")
con.execute(f"CREATE OR REPLACE TABLE normalized_citations_level1 AS SELECT * FROM {csv_safe(normalized_citations_level1_csv)};")
log_vertex_count(con, "normalized_citations_level1")
con.execute(f"CREATE OR REPLACE TABLE link_nobellaureates AS SELECT * FROM {csv_safe(link_nobellaureates_csv)};")
log_vertex_count(con, "link_nobellaureates")
con.execute(f"CREATE OR REPLACE TABLE link_patents AS SELECT * FROM {csv_safe(link_patents_csv)};")
log_vertex_count(con, "link_patents")

# affiliated_with(authorid, institution_id)
con.execute(f"""
CREATE OR REPLACE TABLE affiliated_with AS
SELECT authorid, institutionid AS institution_id
FROM {csv_safe_1(paper_author_aff_csv)};
""")
log_vertex_count(con, "affiliated_with")

# contributed_from(paperid, institution_id, authorid)
con.execute(f"""
CREATE OR REPLACE TABLE contributed_from AS
SELECT paperid, institutionid AS institution_id, authorid
FROM {csv_safe_1(paper_author_aff_csv)};
""")
log_vertex_count(con, "contributed_from")

# affl_assoc_affl(institution_id, associated_institution_id, relationship)
con.execute(f"""
CREATE OR REPLACE TABLE affl_assoc_affl AS
SELECT institutionid AS institution_id, associated_institution_id, relationship
FROM {csv_safe_1(affl_assoc_affl_csv)};
""")
log_vertex_count(con, "affl_assoc_affl")
# Authors_Paper(authorid, paperid)
con.execute(f"""
CREATE OR REPLACE TABLE Authors_Paper AS
SELECT authorid, paperid
FROM {csv_safe(paper_author_csv)};
""")
log_vertex_count(con, "Authors_Paper")
# Papers_to_Authors(paperid, authorid)
con.execute(f"""
CREATE OR REPLACE TABLE Papers_to_Authors AS
SELECT paperid, authorid
FROM {csv_safe(paper_author_csv)};
""")
log_vertex_count(con, "Papers_to_Authors")
# PaperFields(paperid, fieldid)
con.execute(f"""
CREATE OR REPLACE TABLE PaperFields AS
SELECT paperid, fieldid
FROM {csv_safe(paperfields_csv)};
""")
log_vertex_count(con, "PaperFields")
# PaperReferences(citing_paperid, cited_paperid)
con.execute(f"""
CREATE OR REPLACE TABLE PaperReferences AS
SELECT citing_paperid, cited_paperid
FROM {csv_safe(paperrefs_csv)};
""")
log_vertex_count(con, "PaperReferences")
# Link_NSF(paperid, award_id)
con.execute(f"""
CREATE OR REPLACE TABLE Link_NSF AS
SELECT paperid, award_id
FROM {csv_safe(link_nsf_csv)};
""")
log_vertex_count(con, "Link_NSF")
# Link_NIH(paperid, award_id)
con.execute(f"""
CREATE OR REPLACE TABLE Link_NIH AS
SELECT paperid, award_id
FROM {csv_safe(link_nih_csv)};
""")
log_vertex_count(con, "Link_NIH")
# Link_ClinicalTrials(paperid, nct_id)
con.execute(f"""
CREATE OR REPLACE TABLE Link_ClinicalTrials AS
SELECT paperid, nct_id
FROM {csv_safe(link_clinicaltrials_csv)};
""")
log_vertex_count(con, "Link_ClinicalTrials")
# link_newsfeed(paperid, newsfeed_id)
con.execute(f"""
CREATE OR REPLACE TABLE link_newsfeed AS
SELECT paperid, newsfeed_id
FROM {csv_safe(link_newsfeed_csv)};
""")
log_vertex_count(con, "link_newsfeed")

con.execute(f"""
CREATE OR REPLACE TABLE link_twitter AS
SELECT paperid, tweet_id
FROM {csv_safe(link_twitter_csv)};
""")
log_vertex_count(con, "link_twitter")
con.execute("""
CREATE OR REPLACE  PROPERTY GRAPH sciscinet_graph
  VERTEX TABLES (
      Papers,
      Authors_Gender,
      Affiliations,
      Fields,
      NSF_Metadata,
      NIH_Metadata,
      clinicaltrials_metadata,
      Newsfeed_Metadata,
      Twitter_Metadata
  )
  EDGE TABLES (
      Papers_to_Authors
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (authorid) REFERENCES Authors_Gender(authorid),

      Authors_Paper
        SOURCE KEY (authorid) REFERENCES Authors_Gender(authorid)
        DESTINATION KEY (paperid) REFERENCES Papers(paperid),

      contributed_from
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (institution_id) REFERENCES Affiliations(institutionid),

      affiliated_with
        SOURCE KEY (authorid) REFERENCES Authors_Gender(authorid)
        DESTINATION KEY (institution_id) REFERENCES Affiliations(institutionid),

      affl_assoc_affl
        SOURCE KEY (institution_id) REFERENCES Affiliations(institutionid)
        DESTINATION KEY (associated_institution_id) REFERENCES Affiliations(institutionid),

      PaperReferences
        SOURCE KEY (citing_paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (cited_paperid) REFERENCES Papers(paperid),

      Link_NSF
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (award_id) REFERENCES NSF_Metadata(award_id),

      Link_NIH
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (award_id) REFERENCES NIH_Metadata(award_id),

      Link_ClinicalTrials
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (nct_id) REFERENCES clinicaltrials_metadata(nct_id),

      link_newsfeed
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (newsfeed_id) REFERENCES Newsfeed_Metadata(newsfeed_id),

      link_twitter
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (tweet_id) REFERENCES Twitter_Metadata(tweet_id),
      PaperFields
        SOURCE KEY (paperid) REFERENCES Papers(paperid)
        DESTINATION KEY (fieldid) REFERENCES Fields(fieldid)
  );
""")

print("Property graph sciscinet_graph created successfully!")
