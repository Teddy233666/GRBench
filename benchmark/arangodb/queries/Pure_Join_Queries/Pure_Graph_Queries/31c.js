var cursor = db._query(`
LET startDoc = DOCUMENT("Papers/W2122344208")

// 第一层：OUTBOUND startDoc PaperReferences 展开
FOR edge1 IN PaperReferences
  FILTER edge1._from == startDoc._id
  LET ref = DOCUMENT(edge1._to)

  FILTER ref.citation_count < 5

  // 第二层：OUTBOUND startDoc link_newsfeed 展开
  FOR edge2 IN link_newsfeed
    FILTER edge2._from == startDoc._id
    LET n = DOCUMENT(edge2._to)

    COLLECT AGGREGATE
      minRef = MIN(ref._key),
      minNSF = MIN(n._key)

RETURN {
  minRef,
  minNSF
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));