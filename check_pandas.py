import pandas as pd

# print(pd.__version__)

df = pd.DataFrame({
    "模型": ["通义千问", "DeepSeek", "GLM-4"],  # 第 1 列
    "分数": [85, 92, 78],                       # 第 2 列
    "通过": [True, True, False]                  # 第 3 列
})

print(df)
# print(df['分数'])               #index和value 按列都输出
# print(type(df['分数']))         #<class 'pandas.Series'>
# print(df["分数"].values)        #[85 92 78]