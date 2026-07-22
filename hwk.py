# 从 list of dicts 构造一个 3 行的 DataFrame：
import  pandas as  pd

from model_value import left_d

data = [
    {"任务": "翻译", "模型A": 88, "模型B": 82},
    {"任务": "摘要", "模型A": 75, "模型B": 90},
    {"任务": "问答", "模型A": 93, "模型B": 85},
]

df = pd.DataFrame(data)
print(df.shape)


# 用 df 找出模型A 分数 ≥ 85 的行：

high = df[df["模型A"] >= 85]
print(high)

# 对第 1 节的 eval_data.csv 读入后，按 model 分组，计算每个模型的平均 score：
df = pd.read_csv("eval_data.csv", encoding="utf-8-sig")

model_df = df.groupby("model").agg({"score":"mean"})
print(model_df)

# 用 df 和 meta（model_meta.csv），合并后输出有 "provider" 列的新 DataFrame：

meta = pd.read_csv("model_meta.csv", encoding="utf-8-sig")

merged = df.merge(meta,on="model",how="left")
print(merged)
result = merged[merged["provider"].notna()]
print(result)

# 把 eval_data.csv 中 category="安全" 的记录筛出来，按 model 分组，算各模型的平均 score，结果写到 `safety_report.xlsx`：

safe_df = df[df['category'] == "安全"]
print(safe_df)
safe_model = safe_df.groupby('model').agg({"score":"mean"})
print(safe_model)
safe_model.to_excel("safety_report.xlsx")

safety = df[df["category"] == "安全"]
result = safety.groupby("model")["score"].mean()
print(result)
result.to_excel("safety_report.xlsx")