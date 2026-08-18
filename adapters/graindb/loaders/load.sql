exit
CREATE TABLE Papers (
    paperid VARCHAR PRIMARY KEY,
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
    disruption  VARCHAR,
    Atyp_Median_Z  VARCHAR,
    Atyp_10pct_Z  VARCHAR,
    Atyp_Pairs  VARCHAR,
    WSB_mu  VARCHAR,
    WSB_sigma  VARCHAR,
    WSB_Cinf  VARCHAR,
    SB_B  VARCHAR,
    SB_T  VARCHAR,
    team_size BIGINT,
    institution_count BIGINT,
    patent_count BIGINT,
    newsfeed_count BIGINT,
    nct_count BIGINT,
    nih_count BIGINT,
    nsf_count BIGINT
);
COPY Papers
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_papers.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE Authors_Gender (
    authorid VARCHAR PRIMARY KEY,
    avg_c10  VARCHAR,
    avg_logc10  VARCHAR,
    productivity BIGINT,
    h_index BIGINT,
    display_name VARCHAR,
    inference_sources BIGINT,
    inference_counts BIGINT,
    p_gf  VARCHAR
);
COPY Authors_Gender
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_authors.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE Affiliations (
    institutionid VARCHAR PRIMARY KEY,
    display_name VARCHAR,
    ror VARCHAR,
    homepage_url VARCHAR,
    country_code VARCHAR,
    type VARCHAR,
    h_index  VARCHAR,
    productivity  VARCHAR,
    avg_c10  VARCHAR,
    avg_logc10  VARCHAR
);
COPY Affiliations
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_affiliations.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE Fields (
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
    updated_date  VARCHAR,
    fieldid VARCHAR PRIMARY KEY
);
COPY Fields
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_fields.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE NSF_Metadata_raw (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR,
    funderid VARCHAR
);
COPY NSF_Metadata_raw
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_nsf_metadata.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE NSF_Metadata (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR PRIMARY KEY,
    funderid VARCHAR
);
INSERT INTO NSF_Metadata
SELECT
    paperid,
    doi,
    type_crossref,
    funder_display_name,
    award_id,
    funderid
FROM (
    SELECT DISTINCT ON (award_id)
        paperid,
        doi,
        type_crossref,
        funder_display_name,
        award_id,
        funderid
    FROM NSF_Metadata_raw
    WHERE award_id IS NOT NULL
) t;
DROP TABLE NSF_Metadata_raw;
CREATE  TABLE NIH_Metadata_raw (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR,
    funderid VARCHAR
);
COPY NIH_Metadata_raw
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_nsf_metadata.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE NIH_Metadata (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR PRIMARY KEY,
    funderid VARCHAR
);

INSERT INTO NIH_Metadata
SELECT
    paperid,
    doi,
    type_crossref,
    funder_display_name,
    award_id,
    funderid
FROM (
    SELECT DISTINCT ON (award_id)
        paperid,
        doi,
        type_crossref,
        funder_display_name,
        award_id,
        funderid
    FROM NIH_Metadata_raw
    WHERE award_id IS NOT NULL
) t;
DROP TABLE NIH_Metadata_raw;
CREATE TABLE clinicaltrials_metadata_raw (
    paperid VARCHAR,
    nct_id VARCHAR,
    pmid BIGINT,
    pmcid BIGINT,
    doi VARCHAR,
    reference_type VARCHAR,
    citation VARCHAR
);
COPY clinicaltrials_metadata_raw
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_clinicaltrials_metadata.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE clinicaltrials_metadata (
    paperid VARCHAR,
    nct_id VARCHAR PRIMARY KEY,
    pmid BIGINT,
    pmcid BIGINT,
    doi VARCHAR,
    reference_type VARCHAR,
    citation VARCHAR
);

INSERT INTO clinicaltrials_metadata
SELECT
    paperid,
    nct_id,
    pmid,
    pmcid,
    doi,
    reference_type,
    citation
FROM (
    SELECT DISTINCT ON (nct_id)
    paperid,
    nct_id,
    pmid,
    pmcid,
    doi,
    reference_type,
    citation
    FROM clinicaltrials_metadata_raw
    WHERE nct_id IS NOT NULL
) t;
DROP TABLE clinicaltrials_metadata_raw;
CREATE TABLE Newsfeed_Metadata_raw (
    paperid VARCHAR,
    doi VARCHAR,
    subj_id VARCHAR,
    newsfeed_id VARCHAR,
    timestamp  VARCHAR
);
COPY Newsfeed_Metadata_raw
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_newsfeed_metadata.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE Newsfeed_Metadata (
    paperid VARCHAR,
    doi VARCHAR,
    subj_id VARCHAR,
    newsfeed_id VARCHAR PRIMARY KEY,
    timestamp  VARCHAR
);
INSERT INTO Newsfeed_Metadata
SELECT
    paperid,
    doi  ,
    subj_id  ,
    newsfeed_id  ,
    timestamp
FROM (
    SELECT DISTINCT ON (newsfeed_id)
    paperid,
    doi  ,
    subj_id  ,
    newsfeed_id,
    timestamp
    FROM Newsfeed_Metadata_raw
    WHERE newsfeed_id IS NOT NULL
) t;
DROP TABLE Newsfeed_Metadata_raw;
CREATE TABLE Twitter_Metadata_raw (
    tweet_id BIGINT,
    occurred_time  VARCHAR,
    doi VARCHAR,
    original_tweet_url VARCHAR
);
COPY Twitter_Metadata_raw
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_twitter_metadata.csv'
DELIMITER ','
CSV HEADER;
CREATE TABLE Twitter_Metadata (
    tweet_id BIGINT PRIMARY KEY ,
    occurred_time  VARCHAR,
    doi VARCHAR,
    original_tweet_url VARCHAR
);

INSERT INTO Twitter_Metadata
SELECT
    tweet_id,
    occurred_time,
    doi,
    original_tweet_url
FROM (
    SELECT DISTINCT ON (tweet_id)
    tweet_id,
    occurred_time,
    doi,
    original_tweet_url
    FROM Twitter_Metadata_raw
    WHERE tweet_id IS NOT NULL
) t;
CREATE   TABLE Papers_to_Authors (
    start_id VARCHAR,
    start_vertex_type VARCHAR,
    end_id VARCHAR,
    end_vertex_type VARCHAR,
    authorid VARCHAR,
    display_name VARCHAR,
    paperid VARCHAR
);
COPY Papers_to_Authors
FROM 'legacy_host_data/grbench/sf10_1_postgresql_postgresql/sciscinet_authors_paperid_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE  Authors_Paper (
   authorid VARCHAR,
    display_name VARCHAR,
    paperid VARCHAR
);
COPY Authors_Paper
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_authors_paperid_clean.csv'
DELIMITER ','
CSV HEADER;

CREATE   TABLE affiliated_with (
    institutionid VARCHAR,
    author_position VARCHAR,
    authorid VARCHAR
);
COPY affiliated_with
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_author_affiliation_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE contributed_from (
    paperid VARCHAR,
    author_position VARCHAR,
    authorid VARCHAR,
    institutionid VARCHAR,
    raw_affiliation_string VARCHAR
);
COPY contributed_from
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_paper_author_affiliation_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE affl_assoc_affl (
    institution_id VARCHAR,
    associated_institution_id VARCHAR,
    relationship VARCHAR
);
COPY affl_assoc_affl
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_affl_assoc_affl_clean.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS PaperReferences;
CREATE TABLE PaperReferences (
    start_id VARCHAR,
    start_vertex_type VARCHAR,
    end_id VARCHAR,
    end_vertex_type VARCHAR,
    citing_paperid VARCHAR,
    cited_paperid VARCHAR,
    year BIGINT,
    ref_year BIGINT,
    year_diff BIGINT
);
COPY PaperReferences
FROM 'legacy_host_data/grbench/sf10_1_postgresql_postgresql/sciscinet_paperrefs_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE Link_NSF (
    paperid VARCHAR,
    award_id VARCHAR
);
COPY Link_NSF
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_nsf_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE Link_NIH (
    paperid VARCHAR,
    award_id VARCHAR
);
COPY Link_NIH
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_nih_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE Link_ClinicalTrials (
    paperid VARCHAR,
    nct_id VARCHAR
);
COPY Link_ClinicalTrials
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_clinicaltrials_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE link_newsfeed (
    paperid VARCHAR,
    newsfeed_id VARCHAR
);
COPY link_newsfeed
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_newsfeed_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE   TABLE link_twitter(
    paperid VARCHAR,
    tweet_id BIGINT
);
COPY link_twitter
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_twitter_clean.csv'
DELIMITER ','
CSV HEADER;
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
    Hit_10pct BIGINT
);

DROP TABLE IF EXISTS  hit_papers_level1 CASCADE;
CREATE TABLE hit_papers_level1 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count BIGINT,
    Hit_1pct BIGINT,
    Hit_5pct BIGINT,
    Hit_10pct BIGINT
);

DROP TABLE IF EXISTS normalized_citations_level0 CASCADE;
CREATE TABLE normalized_citations_level0 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count  VARCHAR,
    c0  VARCHAR,
    normalized_citations  VARCHAR,
    level BIGINT
);

DROP TABLE IF EXISTS normalized_citations_level1 CASCADE;
CREATE TABLE normalized_citations_level1 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count  VARCHAR,
    c0  VARCHAR,
    normalized_citations  VARCHAR,
    level BIGINT
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
    license VARCHAR
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
    uspto BIGINT
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
COPY hit_papers_level0
FROM 'legacy_host_data/grbench/sf10_1_postgresql_postgresql/hit_papers_level0_clean.csv'
DELIMITER ','
CSV HEADER;

COPY hit_papers_level1
FROM 'legacy_host_data/grbench/sf10_1_postgresql_postgresql/hit_papers_level1_clean.csv'
DELIMITER ','
CSV HEADER;
COPY sources
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_sources_clean.csv'
DELIMITER ','
CSV HEADER;
COPY papersources
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_papersources_clean.csv'
DELIMITER ','
CSV HEADER;
COPY link_nobellaureates
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_nobellaureates_clean.csv'
DELIMITER ','
CSV HEADER;
COPY link_patents
FROM 'legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_patents_clean.csv'
DELIMITER ','
CSV HEADER;
CREATE VERTEX Papers ON Papers;
CREATE VERTEX Authors_Gender ON Authors_Gender;
CREATE VERTEX Affiliations ON Affiliations;
CREATE VERTEX Fields ON Fields;
CREATE VERTEX NSF_Metadata ON NSF_Metadata;
CREATE VERTEX NIH_Metadata ON NIH_Metadata;
CREATE VERTEX clinicaltrials_metadata ON clinicaltrials_metadata;
CREATE VERTEX Newsfeed_Metadata ON Newsfeed_Metadata;
CREATE VERTEX Twitter_Metadata ON Twitter_Metadata;
CREATE EDGE Papers_to_Authors ON Papers_to_Authors ( FROM Papers REFERENCES paperid, TO Authors_Gender REFERENCES authorid );
CREATE EDGE contributed_from ON contributed_from ( FROM Papers REFERENCES paperid, TO Affiliations REFERENCES institutionid );
 -- Authors -> Affiliations
CREATE EDGE affiliated_with ON affiliated_with ( FROM Authors_Gender REFERENCES authorid, TO Affiliations REFERENCES institutionid );
 -- Affiliations -> Affiliations
CREATE EDGE affl_assoc_affl ON affl_assoc_affl ( FROM Affiliations REFERENCES institution_id, TO Affiliations REFERENCES associated_institution_id );
   -- Paper -> Paper (引用关系)
CREATE EDGE PaperReferences ON PaperReferences ( FROM Papers REFERENCES citing_paperid, TO Papers REFERENCES cited_paperid );
     -- Papers -> NSF
CREATE EDGE Link_NSF ON Link_NSF ( FROM Papers REFERENCES paperid, TO NSF_Metadata REFERENCES award_id );
      -- Papers -> NIH
CREATE EDGE Link_NIH ON Link_NIH ( FROM Papers REFERENCES paperid, TO NIH_Metadata REFERENCES award_id );
      -- Papers -> ClinicalTrials
CREATE EDGE Link_ClinicalTrials ON Link_ClinicalTrials ( FROM Papers REFERENCES paperid, TO clinicaltrials_metadata REFERENCES nct_id );
      -- Papers -> Newsfeed
CREATE EDGE link_newsfeed ON link_newsfeed ( FROM Papers REFERENCES paperid, TO Newsfeed_Metadata REFERENCES newsfeed_id );
       -- Papers -> Twitter
CREATE EDGE link_twitter ON link_twitter ( FROM Papers REFERENCES paperid, TO Twitter_Metadata REFERENCES tweet_id );
       -- Papers -> Fields
CREATE EDGE PaperFields ON PaperFields ( FROM Papers REFERENCES paperid, TO Fields REFERENCES fieldid );