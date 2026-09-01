-- statement
COPY Papers_to_Authors FROM '{{UPDATE5_PAPERS_TO_AUTHORS_REL}}' (HEADER=true, IGNORE_ERRORS=true);
