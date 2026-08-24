SET memory_limit = '64GB';
PRAGMA threads=32;
CREATE OR REPLACE TABLE Papers AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_papers.csv',
  header=true,
  ignore_errors=true
);
CREATE OR REPLACE TABLE Authors_Gender AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_authors.csv',
  header=true,
  ignore_errors=true
);
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
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_author_details.csv',
  header=false
);
CREATE OR REPLACE TABLE Affiliations AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_affiliations.csv',
  header=true,
  ignore_errors=true
);
CREATE OR REPLACE TABLE sources AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_sources.csv',
  header=true,
  ignore_errors=true
);
CREATE OR REPLACE TABLE papersources AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_papersources.csv',
  header=true,
  ignore_errors=true
);
CREATE OR REPLACE TABLE PaperDetails AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_paperdetails.csv',
  header=true,
  column_names=[
    'paperid','doi','title','display_name','year','date','doctype',
    'cited_by_count','is_retracted','is_paratext','cited_by_api_url',
    'abstract_inverted_index','language'
  ],
  ignore_errors = true
);
CREATE OR REPLACE TABLE Fields AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_fields.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE hit_papers_level1 AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/hit_papers_level1.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE hit_papers_level0 AS
SELECT * FROM read_csv_auto(
  'data/processed/sf10_0/hit_papers_level0.csv',
  header=true,
  ignore_errors=true
);

-- ===============================
-- 关系表（Edges）
-- ===============================

CREATE OR REPLACE TABLE affiliated_with AS
SELECT authorid, institutionid AS institution_id
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_paper_author_affiliation.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE contributed_from AS
SELECT paperid, institutionid AS institution_id, authorid
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_paper_author_affiliation.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE affl_assoc_affl AS
SELECT institutionid AS institution_id,
       associated_institution_id,
       relationship
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_affl_assoc_affl.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE Authors_Paper AS
SELECT authorid, paperid
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_authors_paperid.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE Papers_to_Authors AS
SELECT paperid, authorid
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_authors_paperid.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE PaperFields AS
SELECT paperid, fieldid
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_paperfields.csv',
  header=true,
  ignore_errors=true
);

CREATE OR REPLACE TABLE PaperReferences AS
SELECT citing_paperid, cited_paperid
FROM read_csv_auto(
  'data/processed/sf10_0/sciscinet_paperrefs.csv',
  header=true,
  ignore_errors=true
);

-- ===============================
-- PROPERTY GRAPH
-- ===============================

CREATE OR REPLACE PROPERTY GRAPH sciscinet_graph
  VERTEX TABLES (
    Papers,
    Authors_Gender,
    author_details,
    Affiliations,
    sources,
    papersources,
    PaperDetails,
    Fields,
    hit_papers_level1,
    hit_papers_level0
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

    PaperFields
      SOURCE KEY (paperid) REFERENCES Papers(paperid)
      DESTINATION KEY (fieldid) REFERENCES Fields(fieldid)
  );
