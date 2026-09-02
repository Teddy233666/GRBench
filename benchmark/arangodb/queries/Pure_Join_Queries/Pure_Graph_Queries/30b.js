var cursor = db._query(`
FOR p IN Papers
  FILTER STARTS_WITH(p._key, "W423590139")
  FILTER p.citation_count <=1

  FOR lnih IN Link_NSF
    FILTER lnih.paperid == p._key

    FOR nm IN NSF_Metadata
      FILTER nm.award_id == lnih.award_id
      COLLECT AGGREGATE min_paper = MIN(p._key)

RETURN min_paper
`)
var result = cursor.toArray();
print(JSON.stringify(result));