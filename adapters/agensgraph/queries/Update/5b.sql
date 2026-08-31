LOAD FROM grbench_update5_papers_to_authors AS e
MATCH (p:Papers {paperid: e.paperid})
MATCH (a:Authors_Gender {authorid: e.authorid})
MERGE (p)-[:Papers_to_Authors]->(a);