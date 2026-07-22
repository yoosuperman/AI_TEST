# 从 CSV 读取评测数据 → 筛选 → 分组统计 → 合并元信息 → 输出 Excel 报告

import pandas as pd
from unicodedata import category

df = pd.read_csv('eval_data.csv',encoding="utf-8_sig")
print(df.head(3))
print(f"  列名：{list(df.columns)}")
print(f"  每列类型：\n{df.dtypes}")

#筛选
good = df[(df["score"]>=80)&(df['passed']== True)]
print(good)
print(f'高分且通过条数为{len(good)}')


#分组
category_df = df.groupby("category")

for name,obj in category_df:
    print(name)
    print(obj)

status = category_df.agg({"score":["mean","max","min"],"passed":"sum"})
print(status)


model_stats = df.groupby('model').agg({"score":"mean","tokens":"sum"})
print(model_stats)


try:
    meta = pd.read_csv("model_meta.csv", encoding="utf-8-sig")
    df = df.merge(meta, on="model", how="left")
    print(f"\n[6] 已合并元信息，当前列：{list(df.columns)}")
except FileNotFoundError:
    print(f"\n[6] 未找到 model_meta.csv，跳过合并")

# 7. 写出报告
df.to_excel("eval_report.xlsx", index=False)
df.to_csv("eval_report.csv", index=False, encoding="utf-8-sig")
print(f"\n[7] 报告已生成：eval_report.xlsx 和 eval_report.csv")
print("完成！")