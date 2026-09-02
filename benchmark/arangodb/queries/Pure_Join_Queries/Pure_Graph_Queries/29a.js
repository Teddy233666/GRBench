var cursor = db._query(`
FOR inst IN Affiliations
  FILTER STARTS_WITH(inst._key, "I42101230")

  // 第1跳
  FOR r1 IN affl_assoc_affl
    FILTER r1.institution_id == inst._key

    FOR m1 IN Affiliations
      FILTER m1._key == r1.associated_institution_id

      // 第2跳
      FOR r2 IN affl_assoc_affl
        FILTER r2.institution_id == m1._key

        FOR m2 IN Affiliations
          FILTER m2._key == r2.associated_institution_id

          // 第3跳
          FOR r3 IN affl_assoc_affl
            FILTER r3.institution_id == m2._key

            FOR m3 IN Affiliations
              FILTER m3._key == r3.associated_institution_id

              // 第4跳
              FOR r4 IN affl_assoc_affl
                FILTER r4.institution_id == m3._key

                FOR assoc IN Affiliations
                  FILTER assoc._key == r4.associated_institution_id

                  // 聚合
                  COLLECT AGGREGATE min_assoc = MIN(assoc._key)

RETURN min_assoc
`)
var result = cursor.toArray();
print(JSON.stringify(result));