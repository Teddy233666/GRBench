-- statement
MATCH (p:Papers)-[u:Update5_Papers_to_Authors]->(a:Authors_Gender)
MATCH (p)-[r:Papers_to_Authors]->(a)
DELETE r;
