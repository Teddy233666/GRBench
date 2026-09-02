var cursor = db._query(`
FOR inst0 IN Affiliations
  FILTER STARTS_WITH(inst0._key, "I42101230")

  // 第1跳
  FOR af1 IN affl_assoc_affl
    FILTER af1.institution_id == inst0._key

    FOR inst1 IN Affiliations
      FILTER inst1._key == af1.associated_institution_id

      // 第2跳
      FOR af2 IN affl_assoc_affl
        FILTER af2.institution_id == inst1._key

        FOR inst2 IN Affiliations
          FILTER inst2._key == af2.associated_institution_id

          // 第3跳
          FOR af3 IN affl_assoc_affl
            FILTER af3.institution_id == inst2._key

            FOR inst3 IN Affiliations
              FILTER inst3._key == af3.associated_institution_id

              COLLECT AGGREGATE min_inst = MIN(inst0._key)

RETURN min_inst
`)
var result = cursor.toArray();
print(JSON.stringify(result));