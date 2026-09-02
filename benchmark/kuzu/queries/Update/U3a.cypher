-- statement
MATCH (a:Papers)-[u:Update2_Edges]->(b:Papers)
MATCH (a)-[r:PaperReferences]->(b)
DELETE r;
