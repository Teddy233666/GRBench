-- statement
COPY Authors_Gender FROM '{{UPDATE4_AUTHORS}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY Papers_to_Authors FROM '{{UPDATE6_PAPERS_TO_AUTHORS_REL}}' (HEADER=true, IGNORE_ERRORS=true);

-- statement
COPY affiliated_with FROM '{{UPDATE6_AFFILIATED_WITH_REL}}' (HEADER=true, IGNORE_ERRORS=true);
