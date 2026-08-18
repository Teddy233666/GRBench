DROP TABLE IF EXISTS Papers CASCADE;
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
DROP TABLE IF EXISTS Authors_Gender CASCADE;
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
DROP TABLE IF EXISTS Affiliations CASCADE;
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
DROP TABLE IF EXISTS Fields CASCADE;
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
DROP TABLE IF EXISTS NSF_Metadata CASCADE;
CREATE TABLE NSF_Metadata (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR,
    funderid VARCHAR
);
COPY NSF_Metadata
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_nsf_metadata.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS NIH_Metadata CASCADE;
CREATE  TABLE NIH_Metadata (
    paperid VARCHAR,
    doi VARCHAR,
    type_crossref VARCHAR,
    funder_display_name VARCHAR,
    award_id VARCHAR,
    funderid VARCHAR
);
COPY NIH_Metadata
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_nsf_metadata.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS clinicaltrials_metadata CASCADE;
CREATE TABLE clinicaltrials_metadata (
    paperid VARCHAR,
    nct_id VARCHAR,
    pmid BIGINT,
    pmcid BIGINT,
    doi VARCHAR,
    reference_type VARCHAR,
    citation VARCHAR
);
COPY clinicaltrials_metadata
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_clinicaltrials_metadata.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS NSF_Metadata CASCADE;
CREATE TABLE Newsfeed_Metadata (
    paperid VARCHAR,
    doi VARCHAR,
    subj_id VARCHAR,
    newsfeed_id VARCHAR,
    timestamp  VARCHAR
);
COPY Newsfeed_Metadata
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_newsfeed_metadata.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS Twitter_Metadata CASCADE;
CREATE TABLE Twitter_Metadata (
    tweet_id BIGINT,
    occurred_time  VARCHAR,
    doi VARCHAR,
    original_tweet_url VARCHAR
);
COPY Twitter_Metadata
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_twitter_metadata.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS Papers_to_Authors CASCADE;
CREATE   TABLE Papers_to_Authors (
    authorid VARCHAR,
    display_name VARCHAR,
    paperid VARCHAR
);
COPY Papers_to_Authors
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_authors_paperid.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS Authors_Paper CASCADE;
CREATE   TABLE  Authors_Paper (
   authorid VARCHAR,
    display_name VARCHAR,
    paperid VARCHAR
);
COPY Authors_Paper
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_authors_paperid.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS affiliated_with CASCADE;
CREATE   TABLE affiliated_with (
    institutionid VARCHAR,
    author_position VARCHAR,
    authorid VARCHAR
);
COPY affiliated_with
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_author_affiliation.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS contributed_from CASCADE;
CREATE   TABLE contributed_from (
    paperid VARCHAR,
    author_position VARCHAR,
    authorid VARCHAR,
     institutionid VARCHAR,
    raw_affiliation_string VARCHAR
);
COPY contributed_from
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_paper_author_affiliation.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS affl_assoc_affl CASCADE;
CREATE   TABLE affl_assoc_affl (
    institution_id VARCHAR,
    associated_institution_id VARCHAR,
    relationship VARCHAR
);
COPY affl_assoc_affl
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_affl_assoc_affl.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS PaperReferences CASCADE;
CREATE   TABLE PaperReferences (
    citing_paperid VARCHAR,
    cited_paperid VARCHAR,
    year BIGINT,
    ref_year BIGINT,
    year_diff BIGINT
);
COPY PaperReferences
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_paperrefs.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS Link_NSF CASCADE;
CREATE   TABLE Link_NSF (
    paperid VARCHAR,
    award_id VARCHAR
);
COPY Link_NSF
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_nsf.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS Link_NIH CASCADE;
CREATE   TABLE Link_NIH (
    paperid VARCHAR,
    award_id VARCHAR
);
COPY Link_NIH
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_nih.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS Link_ClinicalTrials CASCADE;
CREATE   TABLE Link_ClinicalTrials (
    paperid VARCHAR,
    nct_id VARCHAR
);
COPY Link_ClinicalTrials
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_clinicaltrials.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS link_newsfeed CASCADE;
CREATE   TABLE link_newsfeed (
    paperid VARCHAR,
    newsfeed_id VARCHAR
);
COPY link_newsfeed
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_newsfeed.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS link_twitter CASCADE;
CREATE   TABLE link_twitter(
    paperid VARCHAR,
    tweet_id BIGINT
);
COPY link_twitter
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_twitter.csv'
DELIMITER ','
CSV HEADER;
DROP TABLE IF EXISTS PaperFields CASCADE;
CREATE   TABLE PaperFields (
    paperid VARCHAR,
    fieldid VARCHAR,
    score_openalex VARCHAR
);
COPY PaperFields
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_paperfields.csv'
DELIMITER ','
CSV HEADER;
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
COPY author_details(
    authorid, orcid, display_name, display_name_alternatives,
    works_count, cited_by_count, last_known_institution, works_api_url, updated_date
)
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_author_details.csv'
DELIMITER ','
CSV HEADER;
COPY hit_papers_level0
FROM 'legacy_host_data/grbench/sf10_/hit_papers_level0.csv'
DELIMITER ','
CSV HEADER;

COPY hit_papers_level1
FROM 'legacy_host_data/grbench/sf10_1/hit_papers_level1.csv'
DELIMITER ','
CSV HEADER;
COPY normalized_citations_level0
FROM 'legacy_host_data/grbench/sf10_1/normalized_citations_level0.csv'
DELIMITER ','
CSV HEADER;

COPY normalized_citations_level1
FROM 'legacy_host_data/grbench/sf10_1/normalized_citations_level1.csv'
DELIMITER ','
CSV HEADER;
COPY sources
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_sources.csv'
DELIMITER ','
CSV HEADER;
COPY papersources
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_papersources.csv'
DELIMITER ','
CSV HEADER;
COPY link_nobellaureates
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_nobellaureates.csv'
DELIMITER ','
CSV HEADER;
COPY link_patents
FROM 'legacy_host_data/grbench/sf10_1/sciscinet_link_patents.csv'
DELIMITER ','
CSV HEADER;