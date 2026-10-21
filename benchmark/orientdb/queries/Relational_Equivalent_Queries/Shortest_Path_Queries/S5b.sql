-- Relational equivalent of S5b; OrientDB SQL over edge/vertex classes.
SELECT MIN(paperid) AS ref_paperid
FROM Papers
WHERE (paperid = 'W4211259235' OR paperid IN (
    SELECT cited_paperid FROM PaperReferences
    WHERE citing_paperid = 'W4211259235'
))
AND citation_count < 80;
