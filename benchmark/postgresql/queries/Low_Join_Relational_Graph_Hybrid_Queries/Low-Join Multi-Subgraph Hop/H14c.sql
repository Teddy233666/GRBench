
SELECT
    MIN(ref.paper_id::text) AS minPaper,
    MIN(ap.author_id::text) AS minAuthor1,
    MIN(nsf.award_id::text) AS award_id,
    MIN(ln.laureate_id::text) AS minNobel,
    MIN(ad.display_name::text) AS minAuthorid2
FROM
cypher('sciscinet_graph', $$
    MATCH (p4:Papers)-[:PaperReferences]->(p5:Papers)
          -[:PaperReferences]->(p6:Papers)
          -[:PaperReferences]->(ref:Papers)
    WHERE p4.paperid = 'W2122344208'
     AND toInteger(ref.citation_count) < 5
    RETURN p4.paperid, ref.paperid
$$) AS ref(paper_id agtype, ref_paper_id agtype)

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (a:Authors_Gender)-[:Authors_Paper]->(p:Papers)
    WHERE toInteger(a.h_index)>80
    RETURN
        a.authorid,
        a.display_name,
        p.paperid,
        p.year,
        p.citation_count
$$) AS ap(
    author_id agtype,
    author_name agtype,
    paper_id agtype,
    paper_year agtype,
    citations agtype
)
ON ap.paper_id::text = ref.ref_paper_id::text

LEFT JOIN
cypher('sciscinet_graph', $$
    MATCH (p2:Papers)-[:Link_NSF]->(n:NSF_Metadata)
    RETURN
        p2.paperid,
        n.award_id,
        n.type_crossref
$$) AS nsf(
    paper_id agtype,
    award_id agtype,
    funder_name agtype
)
ON ref.paper_id::text = nsf.paper_id::text

LEFT JOIN link_nobellaureates ln
    ON ref.paper_id::text = ln.paperid

LEFT JOIN author_details ad
  ON ap.author_id::text = ad.authorid;