import pandas as pd
from numpy.ma.core import left_shift

eval_data = [
    {"model": "qwen", "category": "事实", "score": 85, "passed": True,  "tokens": 120},
    {"model": "qwen", "category": "推理", "score": 72, "passed": False, "tokens": 250},
    {"model": "qwen", "category": "安全", "score": 90, "passed": True,  "tokens": 89},
    {"model": "qwen", "category": "事实", "score": 78, "passed": False, "tokens": 150},
    {"model": "qwen", "category": "推理", "score": 88, "passed": True,  "tokens": 200},
    {"model": "deepseek", "category": "事实", "score": 92, "passed": True,  "tokens": 110},
    {"model": "deepseek", "category": "推理", "score": 80, "passed": True,  "tokens": 230},
    {"model": "deepseek", "category": "安全", "score": 75, "passed": False, "tokens": 95},
    {"model": "deepseek", "category": "事实", "score": 86, "passed": True,  "tokens": 130},
    {"model": "deepseek", "category": "推理", "score": 68, "passed": False, "tokens": 280},
    {"model": "glm", "category": "事实", "score": 81, "passed": True,  "tokens": 105},
    {"model": "glm", "category": "推理", "score": 73, "passed": False, "tokens": 240},
    {"model": "glm", "category": "安全", "score": 95, "passed": True,  "tokens": 88},
    {"model": "glm", "category": "事实", "score": 77, "passed": False, "tokens": 160},
    {"model": "glm", "category": "推理", "score": 84, "passed": True,  "tokens": 195},
]

# df = pd.DataFrame(eval_data)

# print(df)
#
# print(df.shape)  # (15, 5) —— 15行 × 5列
#
# # 自检：15行都进去了吗？
# print(len(df))  # 应该输出 15

# print(df.head())

# print(df.info())

# print(df.describe())
# df.to_csv("eval_data.csv", index=False, encoding="utf-8-sig")   #转成csv

# 重点：和 Day 6 的 csv.reader 对比——一行读入，不用 open/with/for/DictReader
# encoding="utf-8-sig" 防止 Windows 上中文乱码（和 Day 6 一样）
df = pd.read_csv("eval_data.csv", encoding="utf-8-sig")  # 如果文件放在了 code/ 下，用 code/eval_data.csv

# 验证：数据读对了吗？
print(df)
print(df.shape)  # 应该 (15, 5)
print(df.head(3))  # 看前3行，确认列名和数据都对

print(df["score"] >= 80)
high_score = df[df["score"] >= 80]
print(high_score)

good_models = df[(df["score"] >= 80) & (df["passed"] == True)]  # 每个条件加括号
print(good_models.shape)
print(good_models.head())

good = df.query("score >= 80 and passed == True")  # query 里用 and 而不是 &
print(good)
print(good.shape)

qwen_data = df.query("model == 'qwen'")  # 注意：字符串值用单引号
print(qwen_data)
print(qwen_data.shape)

deep1 = df["model"].str.contains("deep")
print(deep1)
deep_data = df[deep1]
print(deep_data)

fact_data = df[df["category"].str.contains("事")]
print(fact_data)
print(fact_data.shape)
df_renamed = df.copy()
df_renamed["model"] = df_renamed["model"].str.replace("qwen", "Qwen")
print(df_renamed)
print(df_renamed["model"].unique())  # 看更新后的 model 值：['Qwen' 'deepseek' 'glm']  unique()去重
# print(df.describe())
grouped = df.groupby("category")
print(grouped["score"].mean())   #分组后 事实 安全 推理 的平均值
print(grouped)
print(type(grouped))
for name, group in grouped:
    print(f"--- {name} ---")
    print(group)
    print()

print(grouped["score"].mean())
print(grouped["score"].agg(["mean", "max", "min", "count"]))
print(df.groupby("model")["score"].mean())
print(df["category"].value_counts())


meta = pd.read_csv('model_meta.csv',encoding='utf-8-sig')

merged = df.merge(meta,on='model',how='left')
print(merged)
print(merged.columns)

meta_missing = pd.DataFrame({
    "model": ["qwen", "deepseek"],   # 少了一行 glm
    "provider": ["阿里", "深度求索"],
    "max_tokens": [8192, 16384]
})

# how="inner"：只有两表都有的 model 才保留——glm 丢了
inner_d = df.merge(meta_missing, on="model", how="inner")
print(inner_d)
# 结果只有 qwen 和 deepseek 的行

# # how="left"：左表所有行保留——glm 的 provider 和 max_tokens 显示 NaN
left_d = df.merge(meta_missing, on="model", how="left")
print(left_d)
# # glm 的行还在，provider 列显示 NaN（Not a Number = 缺失值）