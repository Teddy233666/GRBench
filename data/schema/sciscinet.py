"""Engine-independent schema contract for the GRBench SciSciNet dataset.

The ``canonical_full_v1`` profile maps the 30 authoritative CSV files to
logical vertex, edge, and plain-table definitions.  Adapters may project these
definitions into an engine-specific physical model, but must document every
rename, reversed edge, collapsed label, or skipped input in their coverage
manifest.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Vertex:
    name: str                 # SQL table name (case-sensitive — matches query labels)
    csv: str                  # CSV file name under GRBENCH_DATA_ROOT/<sf>/
    columns: List[Tuple[str, str]]  # (column_name, type)
    primary_key: str
    rename: Optional[List[Tuple[str, str]]] = None  # (csv_column, new_name) — if needed
    csv_columns: Optional[List[Tuple[str, str]]] = None  # explicit CSV columns when AS SELECT


@dataclass
class Edge:
    name: str
    csv: str
    columns: List[Tuple[str, str]]
    from_col: str
    to_col: str
    from_vertex: str
    to_vertex: str
    from_pk: str
    to_pk: str
    self_loop: bool = False
    rename: Optional[List[Tuple[str, str]]] = None
    csv_columns: Optional[List[Tuple[str, str]]] = None


@dataclass
class PlainTable:
    name: str
    csv: str
    columns: List[Tuple[str, str]]
    rename: Optional[List[Tuple[str, str]]] = None
    csv_columns: Optional[List[Tuple[str, str]]] = None


DATA_PROFILE = "canonical_full_v1"


# ---------------------------------------------------------------------------
# Vertex tables
# ---------------------------------------------------------------------------

VERTICES: List[Vertex] = [
    Vertex(
        name="Papers",
        csv="sciscinet_papers.csv",
        primary_key="paperid",
        columns=[
            ("paperid", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("year", "VARCHAR"),         # year is stored as int but some rows may be empty
            ("date", "VARCHAR"),
            ("doctype", "VARCHAR"),
            ("cited_by_count", "BIGINT"),
            ("is_retracted", "VARCHAR"),
            ("reference_count", "BIGINT"),
            ("citation_count", "BIGINT"),
            ("C3", "BIGINT"),
            ("C5", "BIGINT"),
            ("C10", "BIGINT"),
            ("disruption", "DOUBLE"),
            ("Atyp_Median_Z", "DOUBLE"),
            ("Atyp_10pct_Z", "DOUBLE"),
            ("Atyp_Pairs", "DOUBLE"),
            ("WSB_mu", "DOUBLE"),
            ("WSB_sigma", "DOUBLE"),
            ("WSB_Cinf", "DOUBLE"),
            ("SB_B", "DOUBLE"),
            ("SB_T", "DOUBLE"),
            ("team_size", "BIGINT"),
            ("institution_count", "BIGINT"),
            ("patent_count", "BIGINT"),
            ("newsfeed_count", "BIGINT"),
            ("nct_count", "BIGINT"),
            ("nih_count", "BIGINT"),
            ("nsf_count", "BIGINT"),
        ],
    ),
    Vertex(
        name="Authors_Gender",
        csv="sciscinet_authors.csv",
        primary_key="authorid",
        columns=[
            ("authorid", "VARCHAR"),
            ("avg_c10", "DOUBLE"),
            ("avg_logc10", "DOUBLE"),
            ("productivity", "BIGINT"),
            ("h_index", "BIGINT"),
            ("display_name", "VARCHAR"),
            ("inference_sources", "VARCHAR"),
            ("inference_counts", "VARCHAR"),
            ("P_gf", "DOUBLE"),
        ],
        # CSV has column literally named `P(gf)` which is unfriendly; rename.
        rename=[("P(gf)", "P_gf")],
    ),
    Vertex(
        name="Affiliations",
        csv="sciscinet_affiliations.csv",
        primary_key="institutionid",
        columns=[
            ("institutionid", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("ror", "VARCHAR"),
            ("homepage_url", "VARCHAR"),
            ("country_code", "VARCHAR"),
            ("type", "VARCHAR"),
            ("h_index", "DOUBLE"),
            ("productivity", "DOUBLE"),
            ("avg_c10", "DOUBLE"),
            ("avg_logc10", "DOUBLE"),
        ],
    ),
    Vertex(
        name="Fields",
        csv="sciscinet_fields.csv",
        primary_key="fieldid",
        # The fieldid is the LAST column of the CSV; everything before is metadata
        columns=[
            ("id", "VARCHAR"),
            ("wikidata", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("level", "BIGINT"),
            ("description", "VARCHAR"),
            ("works_count", "BIGINT"),
            ("cited_by_count", "BIGINT"),
            ("image_url", "VARCHAR"),
            ("image_thumbnail_url", "VARCHAR"),
            ("works_api_url", "VARCHAR"),
            ("updated_date", "VARCHAR"),
            ("fieldid", "VARCHAR"),
        ],
    ),
    Vertex(
        name="NIH_Metadata",
        csv="sciscinet_nih_metadata.csv",
        primary_key="award_id",
        columns=[
            ("paperid", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("type_crossref", "VARCHAR"),
            ("funder_display_name", "VARCHAR"),
            ("award_id", "VARCHAR"),
            ("funderid", "VARCHAR"),
        ],
    ),
    Vertex(
        name="NSF_Metadata",
        csv="sciscinet_nsf_metadata.csv",
        primary_key="award_id",
        columns=[
            ("paperid", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("type_crossref", "VARCHAR"),
            ("funder_display_name", "VARCHAR"),
            ("award_id", "VARCHAR"),
            ("funderid", "VARCHAR"),
        ],
    ),
    Vertex(
        name="clinicaltrials_metadata",
        csv="sciscinet_clinicaltrials_metadata.csv",
        primary_key="nct_id",
        columns=[
            ("paperid", "VARCHAR"),
            ("nct_id", "VARCHAR"),
            ("pmid", "VARCHAR"),
            ("pmcid", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("reference_type", "VARCHAR"),
            ("citation", "VARCHAR"),
        ],
    ),
    Vertex(
        name="Newsfeed_Metadata",
        csv="sciscinet_newsfeed_metadata.csv",
        primary_key="newsfeed_id",
        columns=[
            ("paperid", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("subj_id", "VARCHAR"),
            ("newsfeed_id", "VARCHAR"),
            ("timestamp", "VARCHAR"),
        ],
    ),
    Vertex(
        name="Twitter_Metadata",
        csv="sciscinet_twitter_metadata.csv",
        primary_key="tweet_id",
        columns=[
            ("tweet_id", "VARCHAR"),
            ("occurred_time", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("original_tweet_url", "VARCHAR"),
        ],
    ),
    Vertex(
        name="PaperDetails",
        csv="sciscinet_paperdetails.csv",
        primary_key="paperid",
        columns=[
            ("paperid", "VARCHAR"),
            ("doi", "VARCHAR"),
            ("title", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("year", "VARCHAR"),
            ("date", "VARCHAR"),
            ("doctype", "VARCHAR"),
            ("cited_by_count", "BIGINT"),
            ("is_retracted", "VARCHAR"),
            ("is_paratext", "VARCHAR"),
            ("cited_by_api_url", "VARCHAR"),
            ("abstract_inverted_index", "VARCHAR"),
            ("language", "VARCHAR"),
        ],
    ),
]

# ---------------------------------------------------------------------------
# Edge tables
# ---------------------------------------------------------------------------
#
# Notes on column renames:
# - affl_assoc_affl: CSV col `institutionid` → query col `institution_id`
# - contributed_from: source is sciscinet_paper_author_affiliation.csv with
#   columns (paperid, author_position, authorid, institutionid,
#   raw_affiliation_string). The query expects (paperid, institution_id).
# - Authors_Paper: CSV is sciscinet_authors_paperid.csv with
#   (authorid, display_name, paperid). Query expects (paperid, authorid).
# ---------------------------------------------------------------------------

EDGES: List[Edge] = [
    Edge(
        name="Link_NIH",
        csv="sciscinet_link_nih.csv",
        columns=[("paperid", "VARCHAR"), ("award_id", "VARCHAR")],
        from_col="paperid",
        to_col="award_id",
        from_vertex="Papers",
        to_vertex="NIH_Metadata",
        from_pk="paperid",
        to_pk="award_id",
    ),
    Edge(
        name="Link_NSF",
        csv="sciscinet_link_nsf.csv",
        columns=[("paperid", "VARCHAR"), ("award_id", "VARCHAR")],
        from_col="paperid",
        to_col="award_id",
        from_vertex="Papers",
        to_vertex="NSF_Metadata",
        from_pk="paperid",
        to_pk="award_id",
    ),
    Edge(
        name="Link_ClinicalTrials",
        csv="sciscinet_link_clinicaltrials.csv",
        columns=[("paperid", "VARCHAR"), ("nct_id", "VARCHAR")],
        from_col="paperid",
        to_col="nct_id",
        from_vertex="Papers",
        to_vertex="clinicaltrials_metadata",
        from_pk="paperid",
        to_pk="nct_id",
    ),
    # Queries use both casings `Link_Newsfeed` and `link_newsfeed`. DuckDB is
    # case-insensitive on identifiers by default, so a single CREATE TABLE
    # named `link_newsfeed` is sufficient.
    Edge(
        name="link_newsfeed",
        csv="sciscinet_link_newsfeed.csv",
        columns=[("paperid", "VARCHAR"), ("newsfeed_id", "VARCHAR")],
        from_col="paperid",
        to_col="newsfeed_id",
        from_vertex="Papers",
        to_vertex="Newsfeed_Metadata",
        from_pk="paperid",
        to_pk="newsfeed_id",
    ),
    Edge(
        name="Authors_Paper",
        csv="sciscinet_authors_paperid.csv",
        columns=[("authorid", "VARCHAR"), ("paperid", "VARCHAR")],
        csv_columns=[
            ("authorid", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("paperid", "VARCHAR"),
        ],
        rename=[("authorid", "authorid"), ("paperid", "paperid")],
        from_col="authorid",
        to_col="paperid",
        from_vertex="Authors_Gender",
        to_vertex="Papers",
        from_pk="authorid",
        to_pk="paperid",
    ),
    Edge(
        name="Papers_to_Authors",
        csv="sciscinet_authors_paperid.csv",
        columns=[("paperid", "VARCHAR"), ("authorid", "VARCHAR")],
        csv_columns=[
            ("authorid", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("paperid", "VARCHAR"),
        ],
        rename=[("paperid", "paperid"), ("authorid", "authorid")],
        from_col="paperid",
        to_col="authorid",
        from_vertex="Papers",
        to_vertex="Authors_Gender",
        from_pk="paperid",
        to_pk="authorid",
    ),
    Edge(
        name="PaperFields",
        csv="sciscinet_paperfields.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("fieldid", "VARCHAR"),
            ("score_openalex", "DOUBLE"),
        ],
        from_col="paperid",
        to_col="fieldid",
        from_vertex="Papers",
        to_vertex="Fields",
        from_pk="paperid",
        to_pk="fieldid",
    ),
    Edge(
        name="PaperReferences",
        csv="sciscinet_paperrefs.csv",
        columns=[
            ("citing_paperid", "VARCHAR"),
            ("cited_paperid", "VARCHAR"),
            ("year", "VARCHAR"),
            ("ref_year", "VARCHAR"),
            ("year_diff", "BIGINT"),
        ],
        from_col="citing_paperid",
        to_col="cited_paperid",
        from_vertex="Papers",
        to_vertex="Papers",
        from_pk="paperid",
        to_pk="paperid",
        self_loop=True,
    ),
    Edge(
        name="affl_assoc_affl",
        csv="sciscinet_affl_assoc_affl.csv",
        # rename `institutionid` → `institution_id`
        columns=[
            ("institution_id", "VARCHAR"),
            ("associated_institution_id", "VARCHAR"),
            ("relationship", "VARCHAR"),
        ],
        csv_columns=[
            ("institutionid", "VARCHAR"),
            ("associated_institution_id", "VARCHAR"),
            ("relationship", "VARCHAR"),
        ],
        rename=[
            ("institutionid", "institution_id"),
            ("associated_institution_id", "associated_institution_id"),
            ("relationship", "relationship"),
        ],
        from_col="institution_id",
        to_col="associated_institution_id",
        from_vertex="Affiliations",
        to_vertex="Affiliations",
        from_pk="institutionid",
        to_pk="institutionid",
        self_loop=True,
    ),
    Edge(
        name="contributed_from",
        csv="sciscinet_paper_author_affiliation.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("author_position", "VARCHAR"),
            ("authorid", "VARCHAR"),
            ("institution_id", "VARCHAR"),
            ("raw_affiliation_string", "VARCHAR"),
        ],
        csv_columns=[
            ("paperid", "VARCHAR"),
            ("author_position", "VARCHAR"),
            ("authorid", "VARCHAR"),
            ("institutionid", "VARCHAR"),
            ("raw_affiliation_string", "VARCHAR"),
        ],
        rename=[
            ("paperid", "paperid"),
            ("author_position", "author_position"),
            ("authorid", "authorid"),
            ("institutionid", "institution_id"),
            ("raw_affiliation_string", "raw_affiliation_string"),
        ],
        from_col="paperid",
        to_col="institution_id",
        from_vertex="Papers",
        to_vertex="Affiliations",
        from_pk="paperid",
        to_pk="institutionid",
    ),
    Edge(
        name="affiliated_with",
        csv="sciscinet_author_affiliation.csv",
        columns=[
            ("authorid", "VARCHAR"),
            ("institution_id", "VARCHAR"),
            ("author_position", "VARCHAR"),
        ],
        csv_columns=[
            ("institutionid", "VARCHAR"),
            ("author_position", "VARCHAR"),
            ("authorid", "VARCHAR"),
        ],
        rename=[
            ("authorid", "authorid"),
            ("institutionid", "institution_id"),
            ("author_position", "author_position"),
        ],
        from_col="authorid",
        to_col="institution_id",
        from_vertex="Authors_Gender",
        to_vertex="Affiliations",
        from_pk="authorid",
        to_pk="institutionid",
    ),
    Edge(
        name="link_twitter",
        csv="sciscinet_link_twitter.csv",
        columns=[("paperid", "VARCHAR"), ("tweet_id", "VARCHAR")],
        from_col="paperid",
        to_col="tweet_id",
        from_vertex="Papers",
        to_vertex="Twitter_Metadata",
        from_pk="paperid",
        to_pk="tweet_id",
    ),
]


# ---------------------------------------------------------------------------
# Plain tables (referenced by RH/RG relational equivalents; no RAI needed)
# ---------------------------------------------------------------------------

PLAINS: List[PlainTable] = [
    PlainTable(
        name="papersources",
        csv="sciscinet_papersources.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("sourceid", "VARCHAR"),
            ("landing_page_url", "VARCHAR"),
            ("pdf_url", "VARCHAR"),
            ("is_oa", "VARCHAR"),
            ("version", "VARCHAR"),
            ("license", "VARCHAR"),
        ],
    ),
    PlainTable(
        name="sources",
        csv="sciscinet_sources.csv",
        columns=[
            ("sourceid", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("issn", "VARCHAR"),
            ("publisher", "VARCHAR"),
            ("homepage_url", "VARCHAR"),
            ("is_oa", "VARCHAR"),
        ],
    ),
    PlainTable(
        name="link_nobellaureates",
        csv="sciscinet_link_nobellaureates.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("laureate_id", "VARCHAR"),
            ("type", "VARCHAR"),
        ],
    ),
    PlainTable(
        name="link_patents",
        csv="sciscinet_link_patents.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("patent", "VARCHAR"),
            ("uspto", "VARCHAR"),
        ],
    ),
    PlainTable(
        name="author_details",
        csv="sciscinet_author_details.csv",
        columns=[
            ("authorid", "VARCHAR"),
            ("orcid", "VARCHAR"),
            ("display_name", "VARCHAR"),
            ("display_name_alternatives", "VARCHAR"),
            ("works_count", "BIGINT"),
            ("cited_by_count", "BIGINT"),
            ("last_known_institution", "VARCHAR"),
            ("works_api_url", "VARCHAR"),
            ("updated_date", "VARCHAR"),
        ],
    ),
    PlainTable(
        name="hit_papers_level0",
        csv="hit_papers_level0.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("fieldid", "VARCHAR"),
            ("year", "VARCHAR"),
            ("citation_count", "BIGINT"),
            ("Hit_1pct", "BIGINT"),
            ("Hit_5pct", "BIGINT"),
            ("Hit_10pct", "BIGINT"),
        ],
    ),
    PlainTable(
        name="hit_papers_level1",
        csv="hit_papers_level1.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("fieldid", "VARCHAR"),
            ("year", "VARCHAR"),
            ("citation_count", "BIGINT"),
            ("Hit_1pct", "BIGINT"),
            ("Hit_5pct", "BIGINT"),
            ("Hit_10pct", "BIGINT"),
        ],
    ),
    PlainTable(
        name="normalized_citations_level0",
        csv="normalized_citations_level0.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("fieldid", "VARCHAR"),
            ("year", "VARCHAR"),
            ("citation_count", "DOUBLE"),
            ("c0", "DOUBLE"),
            ("normalized_citations", "DOUBLE"),
            ("level", "BIGINT"),
        ],
    ),
    PlainTable(
        name="normalized_citations_level1",
        csv="normalized_citations_level1.csv",
        columns=[
            ("paperid", "VARCHAR"),
            ("fieldid", "VARCHAR"),
            ("year", "VARCHAR"),
            ("citation_count", "DOUBLE"),
            ("c0", "DOUBLE"),
            ("normalized_citations", "DOUBLE"),
            ("level", "BIGINT"),
        ],
    ),
]


TABLE_ALIASES = {"Link_Newsfeed": "link_newsfeed"}


def source_csvs() -> List[str]:
    """Return the unique CSV inputs required by ``canonical_full_v1``."""
    tables = [*VERTICES, *EDGES, *PLAINS]
    return sorted({table.csv for table in tables})
