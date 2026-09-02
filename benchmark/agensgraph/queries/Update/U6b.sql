LOAD FROM grbench_update6_papers_to_authors AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (a:Authors_Gender {authorid: e.authorid})
MERGE (p)-[:Papers_to_Authors]->(a);

LOAD FROM grbench_update6_affiliated_with AS e
MATCH (a:Authors_Gender {authorid: e.authorid})
MATCH (i:Affiliations {institutionid: e.institutionid})
MERGE (a)-[:affiliated_with]->(i);
