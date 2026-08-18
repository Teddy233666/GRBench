SELECT *
FROM cypher('sciscinet_graph', $$
    MATCH (p:Papers)
    WHERE toInteger(p.year) >= 2020 AND toInteger(p.year) <= 2025
    DELETE p
$$) AS (v agtype);
