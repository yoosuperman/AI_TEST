# day40_langsmith_demo.py — LangSmith 最简体验：用 @traceable 记录函数调用
import os
from dotenv import load_dotenv
load_dotenv()                         # 加载 .env 中的 LANGSMITH_API_KEY 等配置
os.environ["LANGSMITH_PROJECT"] = "day40-quickstart"  # 指定项目名（可选，方便在 UI 中查找）

from langsmith import traceable       # 重点：核心装饰器，给函数戴上"追踪眼镜"

@traceable                            # 重点：函数每次调用都会被 LangSmith 记录
def greet(name: str) -> str:
    """简单问候函数 — 每次调用都会被 LangSmith 记录下来"""
    return f"Hello, {name}! Welcome to LangSmith."

@traceable                            # 重点：pipeline 内部调用 greet，会形成嵌套 trace
def pipeline(question: str) -> str:
    """模拟一个简单处理流水线：获取上下文 → 返回回答"""
    context = f"相关知识：{question} 是 AI 测试中的重要概念。"
    result = greet(question)          # greet 会自动作为 pipeline 的"子步骤"被追踪
    return f"{result}\n{context}"

if __name__ == "__main__":
    print(pipeline("可观测性"))
    print("\n✅ Trace 已发送到 LangSmith！打开 https://smith.langchain.com 查看。")