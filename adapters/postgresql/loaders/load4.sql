CREATE EXTENSION IF NOT EXISTS age;
LOAD 'age';
SET search_path = ag_catalog, "$user", public;
SELECT create_graph('sciscinet_graph');
SELECT create_vlabel('sciscinet_graph','Papers');
SELECT load_labels_from_file('sciscinet_graph',
                      'Papers',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_papers.csv');
SELECT create_vlabel('sciscinet_graph','Authors_Gender');

SELECT load_labels_from_file('sciscinet_graph',
                      'Authors_Gender',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_authors.csv');
SELECT create_vlabel('sciscinet_graph','Affiliations');
SELECT load_labels_from_file('sciscinet_graph',
                      'Affiliations',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_affiliations.csv');
SELECT create_vlabel('sciscinet_graph','Fields');
SELECT load_labels_from_file('sciscinet_graph',
                      'Fields',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_fields.csv');
SELECT create_vlabel('sciscinet_graph','NSF_Metadata');
SELECT load_labels_from_file('sciscinet_graph',
                      'NSF_Metadata',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_nsf_metadata.csv');
SELECT create_vlabel('sciscinet_graph','NIH_Metadata');
SELECT load_labels_from_file('sciscinet_graph',
                      'NIH_Metadata',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_nih_metadata.csv');
SELECT create_vlabel('sciscinet_graph','clinicaltrials_metadata');
SELECT load_labels_from_file('sciscinet_graph',
                      'clinicaltrials_metadata',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_clinicaltrials_metadata.csv');
SELECT create_vlabel('sciscinet_graph','Newsfeed_Metadata');
SELECT load_labels_from_file('sciscinet_graph',
                      'Newsfeed_Metadata',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_newsfeed_metadata.csv');
SELECT create_vlabel('sciscinet_graph','Twitter_Metadata');
SELECT load_labels_from_file('sciscinet_graph',
                      'Twitter_Metadata',
                      'legacy_host_data/grbench/sf10_4_postgresql/sciscinet_twitter_metadata.csv');
SELECT create_elabel('sciscinet_graph','Papers_to_Authors');
SELECT load_edges_from_file('sciscinet_graph', 'Papers_to_Authors','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_authors_paperid.csv');
SELECT create_elabel('sciscinet_graph','affiliated_with');
SELECT load_edges_from_file('sciscinet_graph', 'affiliated_with','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_author_affiliation.csv');
SELECT create_elabel('sciscinet_graph','contributed_from');
SELECT load_edges_from_file('sciscinet_graph', 'contributed_from','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_paper_author_affiliation.csv');
SELECT create_elabel('sciscinet_graph','affl_assoc_affl');
SELECT load_edges_from_file('sciscinet_graph', 'affl_assoc_affl','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_affl_assoc_affl.csv');
SELECT create_elabel('sciscinet_graph','PaperReferences');
SELECT load_edges_from_file('sciscinet_graph', 'PaperReferences','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_paperrefs.csv');
SELECT create_elabel('sciscinet_graph','Link_NSF');
SELECT load_edges_from_file('sciscinet_graph', 'Link_NSF','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_link_nsf.csv');

SELECT create_elabel('sciscinet_graph','Link_NIH');
SELECT load_edges_from_file('sciscinet_graph', 'Link_NIH','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_link_nih.csv');

SELECT create_elabel('sciscinet_graph','Link_ClinicalTrials');
SELECT load_edges_from_file('sciscinet_graph', 'Link_ClinicalTrials','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_link_clinicaltrials.csv');

SELECT create_elabel('sciscinet_graph','link_newsfeed');
SELECT load_edges_from_file('sciscinet_graph', 'link_newsfeed','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_link_newsfeed.csv');

SELECT create_elabel('sciscinet_graph','link_twitter');
SELECT load_edges_from_file('sciscinet_graph', 'link_twitter','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_link_twitter.csv');

SELECT create_elabel('sciscinet_graph','PaperFields');
SELECT load_edges_from_file('sciscinet_graph', 'PaperFields','legacy_host_data/grbench/sf10_4_postgresql/sciscinet_paperfields.csv');
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
CREATE TABLE hit_papers_level0 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count BIGINT,
    Hit_1pct BIGINT,
    Hit_5pct BIGINT,
    Hit_10pct BIGINT
);

CREATE TABLE hit_papers_level1 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count BIGINT,
    Hit_1pct BIGINT,
    Hit_5pct BIGINT,
    Hit_10pct BIGINT
);

CREATE TABLE normalized_citations_level0 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count  VARCHAR,
    c0  VARCHAR,
    normalized_citations  VARCHAR,
    level BIGINT
);

CREATE TABLE normalized_citations_level1 (
    paperid VARCHAR,
    fieldid VARCHAR,
    year BIGINT,
    citation_count  VARCHAR,
    c0  VARCHAR,
    normalized_citations  VARCHAR,
    level BIGINT
);

CREATE TABLE sources (
    sourceid VARCHAR PRIMARY KEY,
    display_name VARCHAR,
    issn VARCHAR,
    publisher VARCHAR,
    homepage_url VARCHAR,
    is_oa BOOLEAN
);


CREATE TABLE papersources (
    paperid VARCHAR,
    sourceid VARCHAR,
    landing_page_url VARCHAR,
    pdf_url VARCHAR,
    is_oa BOOLEAN,
    version VARCHAR,
    license VARCHAR
);



CREATE TABLE link_nobellaureates (
    paperid VARCHAR,
    laureate_id BIGINT,
    type BIGINT
);



CREATE TABLE link_patents (
    paperid VARCHAR,
    patent VARCHAR,
    uspto BIGINT
);


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
FROM 'legacy_host_data/grbench/sf10_4/sciscinet_author_details.csv'
DELIMITER ','
CSV HEADER;
COPY hit_papers_level0
FROM 'legacy_host_data/grbench/sf10_4/hit_papers_level0.csv'
DELIMITER ','
CSV HEADER;

COPY hit_papers_level1
FROM 'legacy_host_data/grbench/sf10_4/hit_papers_level1.csv'
DELIMITER ','
CSV HEADER;
COPY normalized_citations_level0
FROM 'legacy_host_data/grbench/sf10_4/normalized_citations_level0.csv'
DELIMITER ','
CSV HEADER;

COPY normalized_citations_level1
FROM 'legacy_host_data/grbench/sf10_4/normalized_citations_level1.csv'
DELIMITER ','
CSV HEADER;
COPY sources
FROM 'legacy_host_data/grbench/sf10_4/sciscinet_sources.csv'
DELIMITER ','
CSV HEADER;
COPY papersources
FROM 'legacy_host_data/grbench/sf10_4/sciscinet_papersources.csv'
DELIMITER ','
CSV HEADER;
COPY link_nobellaureates
FROM 'legacy_host_data/grbench/sf10_4/sciscinet_link_nobellaureates.csv'
DELIMITER ','
CSV HEADER;
COPY link_patents
FROM 'legacy_host_data/grbench/sf10_4/sciscinet_link_patents.csv'
DELIMITER ','
CSV HEADER;
COPY PaperDetails
FROM 'legacy_host_data/grbench/sf10_4/sciscinet_paperdetails.csv'
DELIMITER ','
CSV HEADER;