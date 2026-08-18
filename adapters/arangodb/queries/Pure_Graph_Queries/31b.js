var cursor = db._query(`
LET paths = (
  FOR p5 IN 1..1 OUTBOUND "Papers/W2122344208" PaperReferences
    FOR p6 IN 1..1 OUTBOUND p5 PaperReferences
      FOR p3 IN 1..1 OUTBOUND p6 PaperReferences
        FILTER p3.citation_count < 80
        RETURN p3
)
LET fields = (
  FOR p3 IN paths
    FOR field IN 1..1 OUTBOUND p3 PaperFields
      RETURN field.fieldid
)
RETURN {
  p3: MIN(paths[*].paperid),
  fieldid: MIN(fields)
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));
