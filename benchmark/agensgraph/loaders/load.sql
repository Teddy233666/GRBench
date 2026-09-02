-- 已存在也不会报错
CREATE EXTENSION IF NOT EXISTS file_fdw;

CREATE SERVER IF NOT EXISTS import_server
FOREIGN DATA WRAPPER file_fdw;
SET graph_path = sciscinet_graph;
DROP FOREIGN TABLE IF EXISTS papers_profile;
CREATE FOREIGN TABLE papers_profile (
    paperid VARCHAR,
    doi VARCHAR,
    year BIGINT,
    date DATE,
    doctype VARCHAR,
    cited_by_count BIGINT,
    is_retracted BOOLEAN,
    reference_count BIGINT,
    citation_count BIGINT,
    C3 BIGINT,
    C5 BIGINT,
    C10 BIGINT,
    disruption DOUBLE PRECISION,
    Atyp_Median_Z DOUBLE PRECISION,
    Atyp_10pct_Z DOUBLE PRECISION,
    Atyp_Pairs DOUBLE PRECISION,
    WSB_mu DOUBLE PRECISION,
    WSB_sigma DOUBLE PRECISION,
    WSB_Cinf DOUBLE PRECISION,
    SB_B DOUBLE PRECISION,
    SB_T DOUBLE PRECISION,
    team_size BIGINT,
    institution_count BIGINT,
    patent_count BIGINT,
    newsfeed_count BIGINT,
    nct_count BIGINT,
    nih_count BIGINT,
    nsf_count BIGINT
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_papers.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS Papers;

LOAD FROM papers_profile AS p
CREATE (:Papers = to_jsonb(row_to_json(p)));

DROP FOREIGN TABLE IF EXISTS authors_profile;
CREATE FOREIGN TABLE authors_profile (
    authorid VARCHAR,
    avg_c10 DOUBLE PRECISION,
    avg_logc10 DOUBLE PRECISION,
    productivity BIGINT,
    h_index BIGINT,
    display_name VARCHAR,
    inference_sources BIGINT,
    inference_counts BIGINT,
    p_gf DOUBLE PRECISION
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_authors.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS Authors_Gender;

LOAD FROM authors_profile AS a
CREATE (:Authors_Gender = to_jsonb(row_to_json(a)));

DROP FOREIGN TABLE IF EXISTS affiliations_profile;
CREATE FOREIGN TABLE affiliations_profile (
    institutionid VARCHAR,
    display_name VARCHAR,
    ror VARCHAR,
    homepage_url VARCHAR,
    country_code VARCHAR,
    type VARCHAR,
    h_index DOUBLE PRECISION,
    productivity DOUBLE PRECISION,
    avg_c10 DOUBLE PRECISION,
    avg_logc10 DOUBLE PRECISION
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_affiliations.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS Affiliations;

LOAD FROM affiliations_profile AS af
CREATE (:Affiliations = to_jsonb(row_to_json(af)));
DROP FOREIGN TABLE IF EXISTS fields_profile ;
CREATE FOREIGN TABLE fields_profile (
    id VARCHAR,
    wikidata VARCHAR,
    display_name VARCHAR,
    level BIGINT,
    description TEXT,
    works_count BIGINT,
    cited_by_count BIGINT,
    image_url VARCHAR,
    image_thumbnail_url VARCHAR,
    works_api_url VARCHAR,
    updated_date TIMESTAMP,
    fieldid VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_fields.csv',
    DELIMITER ',',
    QUOTE '"',
    NULL ''
);


CREATE VLABEL IF NOT EXISTS Fields;

LOAD FROM fields_profile AS f
CREATE (:Fields = to_jsonb(row_to_json(f)));

DROP FOREIGN TABLE IF EXISTS nsf_profile;
CREATE FOREIGN TABLE nsf_profile (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR,
    funderid VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_nsf_metadata.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS NSF_Metadata;

LOAD FROM nsf_profile AS n
CREATE (:NSF_Metadata = to_jsonb(row_to_json(n)));

DROP FOREIGN TABLE IF EXISTS nih_profile;
CREATE FOREIGN TABLE nih_profile (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR,
    funderid VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_nih_metadata.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS NIH_Metadata;

LOAD FROM nih_profile AS n
CREATE (:NIH_Metadata = to_jsonb(row_to_json(n)));

-- clinicaltrials_metadata
DROP FOREIGN TABLE IF EXISTS clinical_profile;
CREATE FOREIGN TABLE clinical_profile (
    paperid VARCHAR,
    nct_id VARCHAR,
    pmid BIGINT,
    pmcid BIGINT,
    doi VARCHAR,
    reference_type VARCHAR,
    citation VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_clinicaltrials_metadata.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS clinicaltrials_metadata;
LOAD FROM clinical_profile AS c
CREATE (:clinicaltrials_metadata = to_jsonb(row_to_json(c)));

-- Newsfeed_Metadata
DROP FOREIGN TABLE IF EXISTS newsfeed_profile;
CREATE FOREIGN TABLE newsfeed_profile (
    paperid VARCHAR,
    doi VARCHAR,
    subj_id VARCHAR,
    newsfeed_id VARCHAR,
    timestamp TIMESTAMP
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_newsfeed_metadata.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS Newsfeed_Metadata;
LOAD FROM newsfeed_profile AS n
CREATE (:Newsfeed_Metadata = to_jsonb(row_to_json(n)));

-- Twitter_Metadata
DROP FOREIGN TABLE IF EXISTS twitter_profile;
CREATE FOREIGN TABLE twitter_profile (
    tweet_id BIGINT,
    occurred_time TIMESTAMP,
    doi VARCHAR,
    original_tweet_url VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_twitter_metadata.csv',
    DELIMITER ',',
    NULL ''
);

CREATE VLABEL IF NOT EXISTS Twitter_Metadata;
LOAD FROM twitter_profile AS t
CREATE (:Twitter_Metadata = to_jsonb(row_to_json(t)));

DROP FOREIGN TABLE IF EXISTS papers_authors_profile;
CREATE FOREIGN TABLE papers_authors_profile (
    authorid VARCHAR,
    display_name VARCHAR,
    paperid VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_authors_paperid.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS Papers_to_Authors;

LOAD FROM papers_authors_profile AS t
MATCH (p:Papers), (a:Authors_Gender)
WHERE p.paperid = t.paperid
  AND a.authorid = t.authorid
CREATE (p)-[:Papers_to_Authors]->(a);

DROP FOREIGN TABLE IF EXISTS authors_paper_profile;
CREATE FOREIGN TABLE authors_paper_profile (
   authorid VARCHAR,
    display_name VARCHAR,
    paperid VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_authors_paperid.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS Authors_Paper;

LOAD FROM authors_paper_profile AS t
MATCH (a:Authors_Gender), (p:Papers)
WHERE a.authorid = t.authorid
  AND p.paperid= t.paperid
CREATE (a)-[:Authors_Paper]->(p);

DROP FOREIGN TABLE IF EXISTS affiliated_with_profile;
CREATE FOREIGN TABLE affiliated_with_profile (
    institutionid VARCHAR,
    author_position VARCHAR,
    authorid VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_author_affiliation.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS affiliated_with;

LOAD FROM affiliated_with_profile AS t
MATCH (a:Authors_Gender), (i:Affiliations)
WHERE a.authorid= t.authorid
  AND i.institutionid= t.institutionid
CREATE (a)-[:affiliated_with]->(i);

DROP FOREIGN TABLE IF EXISTS contributed_from_profile;
CREATE FOREIGN TABLE contributed_from_profile (
    paperid VARCHAR,
    author_position VARCHAR,
    authorid VARCHAR,
     institutionid VARCHAR,
    raw_affiliation_string VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_paper_author_affiliation.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS contributed_from;

LOAD FROM contributed_from_profile AS t
MATCH (p:Papers), (i:Affiliations)
WHERE p.paperid= t.paperid
  AND i.institutionid= t.institutionid
CREATE (p)-[:contributed_from {authorid: t.authorid}]->(i);

DROP FOREIGN TABLE IF EXISTS affl_assoc_affl_profile;
CREATE FOREIGN TABLE affl_assoc_affl_profile (
    institution_id VARCHAR,
    associated_institution_id VARCHAR,
    relationship VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_affl_assoc_affl.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS affl_assoc_affl;

LOAD FROM affl_assoc_affl_profile AS t
MATCH (i1:Affiliations), (i2:Affiliations)
WHERE i1.institutionid= t.institution_id
  AND i2.institutionid= t.associated_institution_id
CREATE (i1)-[:affl_assoc_affl {relationship: t.relationship}]->(i2);

DROP FOREIGN TABLE IF EXISTS paper_refs_profile;
CREATE FOREIGN TABLE paper_refs_profile (
    citing_paperid VARCHAR,
    cited_paperid VARCHAR,
    year BIGINT,
    ref_year BIGINT,
    year_diff BIGINT
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_paperrefs.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS PaperReferences;

LOAD FROM paper_refs_profile AS t
MATCH (p1:Papers), (p2:Papers)
WHERE p1.paperid= t.citing_paperid
  AND p2.paperid= t.cited_paperid
CREATE (p1)-[:PaperReferences]->(p2);

DROP FOREIGN TABLE IF EXISTS link_nsf_profile;
CREATE FOREIGN TABLE link_nsf_profile (
    paperid VARCHAR,
    award_id VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_link_nsf.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS Link_NSF;

LOAD FROM link_nsf_profile AS t
MATCH (p:Papers), (n:NSF_Metadata)
WHERE p.paperid= t.paperid
  AND n.award_id= t.award_id
CREATE (p)-[:Link_NSF]->(n);

DROP FOREIGN TABLE IF EXISTS link_nih_profile;
CREATE FOREIGN TABLE link_nih_profile (
    paperid VARCHAR,
    award_id VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_link_nih.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS Link_NIH;

LOAD FROM link_nih_profile AS t
MATCH (p:Papers), (n:NIH_Metadata)
WHERE p.paperid= t.paperid
  AND n.award_id= t.award_id
CREATE (p)-[:Link_NIH]->(n);

DROP FOREIGN TABLE IF EXISTS link_clinical_profile;
CREATE FOREIGN TABLE link_clinical_profile (
    paperid VARCHAR,
    nct_id VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_link_clinicaltrials.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS Link_ClinicalTrials;

LOAD FROM link_clinical_profile AS t
MATCH (p:Papers), (c:clinicaltrials_metadata)
WHERE p.paperid= t.paperid
  AND c.nct_id= t.nct_id
CREATE (p)-[:Link_ClinicalTrials]->(c);

DROP FOREIGN TABLE IF EXISTS link_newsfeed_profile;
CREATE FOREIGN TABLE link_newsfeed_profile (
    paperid VARCHAR,
    newsfeed_id VARCHAR
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_link_newsfeed.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS link_newsfeed;

LOAD FROM link_newsfeed_profile AS t
MATCH (p:Papers), (n:Newsfeed_Metadata)
WHERE p.paperid= t.paperid
  AND n.newsfeed_id= t.newsfeed_id
CREATE (p)-[:link_newsfeed]->(n);

DROP FOREIGN TABLE IF EXISTS link_twitter_profile;
CREATE FOREIGN TABLE link_twitter_profile (
    paperid VARCHAR,
    tweet_id BIGINT
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_link_twitter.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS link_twitter;

LOAD FROM link_twitter_profile AS t
MATCH (p:Papers), (tw:Twitter_Metadata)
WHERE p.paperid= t.paperid
  AND tw.tweet_id= t.tweet_id
CREATE (p)-[:link_twitter]->(tw);

DROP FOREIGN TABLE IF EXISTS paper_fields_profile;
CREATE FOREIGN TABLE paper_fields_profile (
    paperid VARCHAR,
    fieldid VARCHAR,
    score_openalex BIGINT
)
SERVER import_server
OPTIONS (
    FORMAT 'csv',
    HEADER 'true',
    FILENAME '{{DATA_DIR}}/sciscinet_paperfields.csv',
    DELIMITER ',',
    NULL ''
);

CREATE ELABEL IF NOT EXISTS PaperFields;

LOAD FROM paper_fields_profile AS t
MATCH (p:Papers), (f:Fields)
WHERE p.paperid= t.paperid
  AND f.fieldid= t.fieldid
CREATE (p)-[:PaperFields]->(f);


DROP TABLE IF EXISTS author_details CASCADE;
CREATE TABLE author_details (
    authorid VARCHAR PRIMARY KEY,
    orcid VARCHAR,
    display_name VARCHAR,
    display_name_alternatives VARCHAR,
    works_count VARCHAR,
    cited_by_count VARCHAR,
    last_known_institution VARCHAR,
    works_api_url VARCHAR,
    updated_date VARCHAR
);
DROP TABLE IF EXISTS hit_papers_level0 CASCADE;
CREATE TABLE hit_papers_level0 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count BIGINT,
    Hit_1pct BIGINT,
    Hit_5pct BIGINT,
    Hit_10pct BIGINT,

    PRIMARY KEY (paperid, fieldid)
);

DROP TABLE IF EXISTS  hit_papers_level1 CASCADE;
CREATE TABLE hit_papers_level1 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count BIGINT,
    Hit_1pct BIGINT,
    Hit_5pct BIGINT,
    Hit_10pct BIGINT,

    PRIMARY KEY (paperid, fieldid)
);

DROP TABLE IF EXISTS normalized_citations_level0 CASCADE;
CREATE TABLE normalized_citations_level0 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count DOUBLE PRECISION,
    c0 DOUBLE PRECISION,
    normalized_citations DOUBLE PRECISION,
    level BIGINT,

    PRIMARY KEY (paperid, fieldid)
);

DROP TABLE IF EXISTS normalized_citations_level1 CASCADE;
CREATE TABLE normalized_citations_level1 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count DOUBLE PRECISION,
    c0 DOUBLE PRECISION,
    normalized_citations DOUBLE PRECISION,
    level BIGINT,

    PRIMARY KEY (paperid, fieldid)
);
DROP TABLE IF EXISTS sources CASCADE;
CREATE TABLE sources (
    sourceid VARCHAR PRIMARY KEY,
    display_name VARCHAR,
    issn VARCHAR,
    publisher VARCHAR,
    homepage_url VARCHAR,
    is_oa BOOLEAN
);


DROP TABLE IF EXISTS papersources CASCADE;
CREATE TABLE papersources (
    paperid VARCHAR,
    sourceid VARCHAR,
    landing_page_url VARCHAR,
    pdf_url VARCHAR,
    is_oa BOOLEAN,
    version VARCHAR,
    license VARCHAR,

    PRIMARY KEY (paperid, sourceid)
);


DROP TABLE IF EXISTS link_nobellaureates CASCADE;
CREATE TABLE link_nobellaureates (
    paperid VARCHAR,
    laureate_id BIGINT,
    type BIGINT
);


DROP TABLE IF EXISTS  link_patents CASCADE;
CREATE TABLE link_patents (
    paperid VARCHAR,
    patent VARCHAR,
    uspto BIGINT,

    PRIMARY KEY (paperid, patent)
);

DROP TABLE IF EXISTS PaperDetails CASCADE;
CREATE TABLE PaperDetails (
    paperid VARCHAR PRIMARY KEY,
    doi VARCHAR,
    title VARCHAR,
    display_name VARCHAR,
    year BIGINT,
    date DATE,
    doctype VARCHAR,
    cited_by_count BIGINT,
    is_retracted BOOLEAN,
    is_paratext BOOLEAN,
    cited_by_api_url VARCHAR,
    abstract_inverted_index TEXT,
    language VARCHAR
);
COPY author_details(
    authorid, orcid, display_name, display_name_alternatives,
    works_count, cited_by_count, last_known_institution, works_api_url, updated_date
)
FROM '{{DATA_DIR}}/sciscinet_author_details.csv'
DELIMITER ','
CSV HEADER;
COPY hit_papers_level0
FROM '{{DATA_DIR}}/hit_papers_level0.csv'
DELIMITER ','
CSV HEADER;

COPY hit_papers_level1
FROM '{{DATA_DIR}}/hit_papers_level1.csv'
DELIMITER ','
CSV HEADER;
COPY normalized_citations_level0
FROM '{{DATA_DIR}}/normalized_citations_level0.csv'
DELIMITER ','
CSV HEADER;

COPY normalized_citations_level1
FROM '{{DATA_DIR}}/normalized_citations_level1.csv'
DELIMITER ','
CSV HEADER;
COPY sources
FROM '{{DATA_DIR}}/sciscinet_sources.csv'
DELIMITER ','
CSV HEADER;
COPY papersources
FROM '{{DATA_DIR}}/sciscinet_papersources.csv'
DELIMITER ','
CSV HEADER;
COPY link_nobellaureates
FROM '{{DATA_DIR}}/sciscinet_link_nobellaureates.csv'
DELIMITER ','
CSV HEADER;
COPY link_patents
FROM '{{DATA_DIR}}/sciscinet_link_patents.csv'
DELIMITER ','
CSV HEADER;
COPY PaperDetails
FROM '{{DATA_DIR}}/sciscinet_paperdetails.csv'
DELIMITER ','
CSV HEADER;
