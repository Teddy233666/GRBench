import pandas as pd

# 1. 读取原始 CSV 文件
df = pd.read_csv("legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_twitter.csv")

# 2. 删除指定的 4 列（如果不存在会自动忽略，不会报错）
drop_cols = ["start_id", "start_vertex_type", "end_id", "end_vertex_type"]
df_clean = df.drop(columns=[col for col in drop_cols if col in df.columns], errors="ignore")

# 3. 保存为新的干净 CSV
df_clean.to_csv("legacy_host_data/grbench/sf10_1_postgresql/sciscinet_link_twitter_clean.csv", index=False)

print("✅ 清洗完成！已生成：sciscinet_paperrefs_clean.csv")
print(f"✅ 原始列数：{len(df.columns)}，清洗后列数：{len(df_clean.columns)}")
print(f"✅ 保留的列：{list(df_clean.columns)}")