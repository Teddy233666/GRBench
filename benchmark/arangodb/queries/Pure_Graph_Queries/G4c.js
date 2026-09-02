var cursor = db._query(`
LET rows = (
  FOR p IN Papers
    FILTER STARTS_WITH(p.paperid, "W423590139")
      AND p.citation_count == 1
    FOR ref IN 1..1 OUTBOUND p PaperReferences
      RETURN { p, ref }
)
LET awards = (
  FOR row IN rows
    FOR nsf IN 1..1 OUTBOUND row.p Link_NSF
      RETURN nsf.award_id
)
RETURN {
  min_ref_paper_id: MIN(rows[*].ref.paperid),
  award_id: MIN(awards)
}
`)
var result = cursor.toArray();
print(JSON.stringify(result));
