MATCH (p:Papers)
WHERE p.year >= 2020 AND p.year <= 2025
DELETE p;