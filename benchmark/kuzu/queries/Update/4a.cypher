-- statement
MATCH (a:Authors_Gender)
WHERE a.h_index >= 10 AND a.h_index <= 20
DETACH DELETE a;
