-- statement
COPY Papers FROM '{{UPDATE1_PAPERS}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY PaperReferences FROM '{{UPDATE3_PAPERREFERENCES_REL}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY Papers_to_Authors FROM '{{UPDATE1_PAPERS_TO_AUTHORS_REL}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY Authors_Paper FROM '{{UPDATE3_AUTHORS_PAPER_REL}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY contributed_from FROM '{{UPDATE3_CONTRIBUTED_FROM_REL}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY PaperFields FROM '{{UPDATE3_PAPERFIELDS_REL}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY link_nsf FROM '{{UPDATE3_LINK_NSF_NODE}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY link_nih FROM '{{UPDATE3_LINK_NIH_NODE}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY link_clinicaltrials FROM '{{UPDATE3_LINK_CLINICALTRIALS_NODE}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY link_newsfeed FROM '{{UPDATE3_LINK_NEWSFEED_NODE}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY link_twitter FROM '{{UPDATE3_LINK_TWITTER_REL}}' (HEADER=true, IGNORE_ERRORS=true);
