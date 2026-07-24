import os
import json
import time
import sys
import requests
import pandas as pd
from dotenv import load_dotenv

# 重点：Windows 默认终端是 GBK 编码，直接 print emoji（如 📊 ✅）会触发 UnicodeEncodeError。
# 把 stdout 重配成 UTF-8，避免脚本在最后一步打印摘要时崩溃。
# 如果你已经在用 PowerShell 7 / VS Code 终端等 UTF-8 环境，这行不影响；
# 在 PyCharm 默认终端或 cmd 里，这行能救命。
sys.stdout.reconfigure(encoding="utf-8")

# ── 配置 ──────────────────────────────────────────────
# 重点：.env 里存 Key，代码里只读环境变量——Day 8 开始就是这个规矩
load_dotenv()
API_KEY = os.getenv("DASHSCOPE_API_KEY")
API_URL = f"{os.getenv("DASHSCOPE_BASE_URL")}/chat/completions"
MODEL = "qwen-turbo"  # 通义千问免费额度够用


# ── 函数 1：构造问题列表 ──────────────────────────────
def build_questions():
    """构造 20 个问题，覆盖简单/中等/困难三档。每个问题是一个 dict。

    返回格式（重点！记住这个结构，后面 batch_call 依赖它）：
        [
            {"question": "什么是Python？", "stream": False},   # 非流式
            {"question": "请用三句话解释量子计算。", "stream": True},  # 流式
            ...
        ]

    为什么返回 list[dict] 而不是 list[str]？
    → 因为流式/非流式是"问题的属性"，不是全局开关。一个问题该用什么模式，
      跟着它自己走，后面 call_one_api() 直接读 dict["stream"] 决定分支。
    """
    # ── TODO 第 2 步：替换下面的空问题列表 ──
    questions = [
        # 前 15 个非流式问题（stream=False），覆盖简单→困难
        # 后 5 个流式问题（stream=True），长回答类
        # ── 简单（6 个）：一句话能说清的问题 ──
        {"question": "什么是Python？", "stream": False},
        {"question": "1+1等于几？", "stream": False},
        {"question": "中国的首都是哪里？", "stream": False},
        {"question": "水的化学式是什么？", "stream": False},
        {"question": "请用中文说'Hello World'。", "stream": False},
        {"question": "一年有几个季节？", "stream": False},

        # ── 中等（5 个）：需要解释/推理的问题 ──
        {"question": "请解释什么是机器学习。", "stream": False},
        {"question": "Python的列表和元组有什么区别？", "stream": False},
        {"question": "什么是面向对象编程？", "stream": False},
        {"question": "请解释HTTP状态码404和500的含义。", "stream": False},
        {"question": "Git中的commit和push有什么区别？", "stream": False},

        # ── 困难（4 个）：需要多步推理或专业知识 ──
        {"question": "请解释大语言模型中的Transformer架构的核心思想。", "stream": False},
        {"question": "在Python中，深拷贝和浅拷贝的区别是什么？请举例说明。", "stream": False},
        {"question": "请解释RESTful API的设计原则。", "stream": False},
        {"question": "什么是并发编程中的死锁？如何避免？", "stream": False},

        # ── 流式（5 个）：长回答类问题，适合看"逐字输出"效果 ──
        {"question": "请用三句话解释量子计算的基本原理。", "stream": True},
        {"question": "请写一首关于编程的五言绝句。", "stream": True},
        {"question": "请用通俗的语言解释什么是区块链。", "stream": True},
        {"question": "请用Python写一个快速排序算法并逐行解释。", "stream": True},
        {"question": "请解释AI测试和传统软件测试的五个主要区别。", "stream": True},
    ]
    return questions


# ── 函数 2：调一次 API ─────────────────────────────────
def call_one_api(question, stream=False):
    """调一次通义千问 API，返回统一格式的 dict。
    不管是流式还是非流式，返回值结构完全一样——外部调用方不关心内部细节。

    参数:
        question: 要问的问题（字符串）
        stream: 是否用流式请求（bool）

    返回（重点！固定结构，存入 list 后直接喂给 pd.DataFrame）:
        {
            "question": "...",       # 原始问题（方便对照）
            "answer": "...",         # 模型回答（非流式→直接取；流式→逐行拼接）
            "tokens": 123,           # total_tokens 消耗量
            "stream": True/False,    # 原样返回，方便后面 Excel 里区分
            "status": "success"      # "success" 或 "error"
        }

    容错策略（重点！）：
        一条失败 ≠ 全部中止。catch 住异常，返回带错误信息的 dict，
        batch_call() 继续跑下一条。避免跑 20 条，第 12 条超时整批白费。
    """

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],  # 只有一个 user 消息
    }

    # 构造请求头（重点：Authorization 的值是 "Bearer " + API Key，中间有空格）
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    # ── 非流式调用 ────────────────────────
    # 重点：if/else 分支在 try 里面，不管哪种模式，异常都被同一个 except 兜底
    try:
        if not stream:
            # 非流式：一个 HTTP 请求 → 等待完整响应 → 一次性拿到全部内容
            resp = requests.post(
                API_URL,
                headers=headers,
                json=payload,  # 重点：post 的 json 参数，不是 data（Day 8 教的）
                timeout=30  # 非流式给 30 秒，够大模型思考完
            )

            # 第一步：检查 HTTP 状态码（200 才算成功）
            if resp.status_code != 200:
                return {
                    "question": question,
                    "answer": f"API返回非200状态码: {resp.status_code}",
                    "tokens": 0,
                    "stream": stream,
                    "status": "error",
                    "http_status": resp.status_code
                }

            # 第二步：解析 JSON 响应体
            # 重点：requests 的 .json() 方法直接把响应体转成 Python dict（Day 8 教的）
            data = resp.json()

            # 第三步：从嵌套 JSON 里提取我们需要的字段
            # 通义千问兼容 OpenAI 格式，回答在 choices[0].message.content
            answer = data["choices"][0]["message"]["content"]

            print(f'问题: {question}\n回答: {answer}')

            # tokens 在 usage 对象里，total_tokens 是输入+输出总消耗
            # 重点：用 .get() 而不是直接取键——某些响应可能没有 usage 字段
            tokens = data.get("usage", {}).get("total_tokens", 0)

            return {
                "question": question,
                "answer": answer,
                "tokens": tokens,
                "stream": stream,
                "status": "success",
                "http_status": resp.status_code
            }
        else:
            # 流式需要告诉 API "请用 SSE（Server-Sent Events）格式逐块返回"
            payload["stream"] = True  # 重点：payload 里加 stream=True
            # 重点：百炼 OpenAI 兼容模式默认不返回 usage，
            # 必须显式声明 stream_options 才能在最后一个 chunk 里拿到 token 消耗
            payload["stream_options"] = {"include_usage": True}

            # stream=True 是 requests 的参数，告诉它"别一次性读完，逐行给我"
            # 重点：stream 在前，timeout 在后——参数顺序无所谓，关键是 keyword 名要对
            resp = requests.post(
                API_URL,
                headers=headers,
                json=payload,
                stream=True,  # 重点：requests 的 stream，不是 payload 里的
                timeout=60  # 流式给 60 秒，因为模型是一边生成一边输出，耗时更长
            )

            # 检查 HTTP 状态码（和非流式一模一样的逻辑）
            if resp.status_code != 200:
                return {
                    "question": question,
                    "answer": f"API返回非200状态码: {resp.status_code}",
                    "tokens": 0,
                    "stream": stream,
                    "status": "error",
                    "http_status": resp.status_code
                }

            # ── 逐行读取 SSE 响应 ──
            # 重点：SSE 格式是 "data: {...json...}\n\n"，每一块数据以 "data:" 开头
            full_answer = ""  # 拼接器，把逐块内容拼成完整回答
            last_chunk_data = {}  # 保存最后一块，其中包含 usage（token 信息）

            # iter_lines() 是 requests 的方法，按行读取流式响应（Day 9 教的）
            for line in resp.iter_lines(decode_unicode=True):
                if not line:
                    continue  # 空行跳过

                if line.startswith("data: "):
                    json_str = line[6:]  # 去掉 "data: " 前缀，6 个字符
                    if json_str.strip() == "[DONE]":
                        break  # OpenAI 兼容格式的结束标记

                    try:
                        chunk = json.loads(json_str)

                        # 重点：先保存 chunk，确保最后一个可能包含 usage 的 chunk 被记录
                        last_chunk_data = chunk

                        # 从 chunk 里提取增量内容
                        # 注意：包含 usage 的最后一个 chunk，choices 是空列表，
                        # 所以必须先用 .get("choices", []) 判断非空，再取 delta。
                        # 否则 chunk["choices"][0] 会触发 IndexError，把脚本搞崩。
                        choices = chunk.get("choices", [])
                        if choices:
                            delta = choices[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                full_answer += content  # 拼接进完整回答
                                # print(content, end="", flush=True)

                    except json.JSONDecodeError:
                        continue  # 个别行解析失败不影响整体

            # ── 从最后一个 chunk 里提取 token 信息 ──
            # 重点：流式的 usage 信息在最后一个 chunk 里返回，
            # 但需要上面设置 stream_options={"include_usage": True} 才会真正出现。
            # 如果没返回 usage，这里会安全地得到 0，而不是报错。
            tokens = last_chunk_data.get("usage", {}).get("total_tokens", 0)

            return {
                "question": question,
                "answer": full_answer,
                "tokens": tokens,
                "stream": stream,
                "status": "success",
                "http_status": resp.status_code
            }
    except requests.exceptions.Timeout:
        # Day 9 教的：超时异常单独处理，返回错误信息而不是让程序崩溃
        return {
            "question": question,
            "answer": "请求超时（30秒）",
            "tokens": 0,
            "stream": stream,
            "status": "error",
            "http_status": None
        }

    except requests.exceptions.ConnectionError:
        # 网络问题（断网/DNS失败）
        return {
            "question": question,
            "answer": "网络连接错误",
            "tokens": 0,
            "stream": stream,
            "status": "error",
            "http_status": None
        }

    except Exception as e:
        # 兜底：任何上面没 catch 到的异常都掉进这里
        # 重点：str(e) 把异常对象转成可读字符串，存进 answer 字段方便排查
        return {
            "question": question,
            "answer": f"未知错误: {str(e)}",
            "tokens": 0,
            "stream": stream,
            "status": "error",
            "http_status": None
        }

    #
    # TODO 第 3 步：实现流式调用
    pass


# ── 函数 3：批量调用 ───────────────────────────────────
def batch_call(questions):
    """循环调 API，逐条收集结果。一条失败不中断整批。

    参数:
        questions: build_questions() 的返回值

    返回:
        list[dict]，每个 dict 是 call_one_api() 的返回值。
        结果列表长度 = 问题数量（不管成功还是失败，每条都有记录）。

    为什么用 list[dict] 收集？
    → 因为 pd.DataFrame(list_of_dicts) 一条语句就能转成表格（Day 13 教的）。
       dict 的 key 自动变成 DataFrame 的列名，value 变成单元格内容。
    """
    results = []  # 重点：空列表当"收集器"，每条调完往里 append

    for i, q in enumerate(questions, 1):
        question_text = q["question"]
        use_stream = q["stream"]

        print(f"[{i}/{len(questions)}] {'流式' if use_stream else '普通'}：{question_text[:30]}...")

        #
        # 提示：别忘了用 try/except 兜底，防止 call_one_api 抛异常时循环中断
        try:
            result = call_one_api(question_text, use_stream)
            results.append(result)  # 把这条结果"收集"进列表
        except Exception as e:
            # 兜底——理论上 call_one_api 内部已经 catch 了所有异常，
            # 但以防万一外层再包一层，确保循环绝对不会中断
            results.append({
                "question": question_text,
                "answer": f"外部异常: {str(e)}",
                "tokens": 0,
                "stream": use_stream,
                "status": "error",
                "http_status": None
            })

        time.sleep(0.5)  # 礼貌性间隔，避免触发限流

    return results


# ── 函数 4：存 Excel ───────────────────────────────────
def save_to_excel(results, filename="api_results.xlsx"):
    """把结果列表转成 DataFrame，存为 Excel。

    参数:
        results: batch_call() 的返回值（list[dict]）
        filename: 输出的 Excel 文件名

    为什么存 Excel 而不是 CSV？
    → Excel 可以直接双击打开看，中文不乱码（CSV 需要指定 encoding）。
       而且面试时展示 Excel 比展示 CSV 专业得多。
    """
    df = pd.DataFrame(results)

    # 第 2 步：加一个统计信息行（放在 DataFrame 末尾，方便一眼看到汇总）
    # 重点：pd.concat 是 Day 13 教的 merge/concat 功能，这里用最简形式
    # 在 concat 之前把 total_tokens 算好存起来——concat 之后统计行本身也包含
    # tokens 总和值，再 sum 一次会翻倍。
    total_tokens = df["tokens"].sum()  # 20 条 API 调用的实际总消耗
    success_before = df[df["status"] == "success"].shape[0]

    summary = pd.DataFrame([{
        "question": "【统计】",
        "answer": f"共{len(results)}条, "
                  f"成功{success_before}条, "
                  f"总Token: {total_tokens}",
        "tokens": total_tokens,  # 统计行也记一份，Excel 里能看到
        "stream": "",
        "status": "",
        "http_status": ""
    }])
    df = pd.concat([df, summary], ignore_index=True)

    # 第 3 步：写 Excel
    # 重点：index=False 不加的话 Excel 会多一列数字编号（DataFrame 的行索引）
    df.to_excel(filename, index=False)

    # 第 4 步：打印摘要，让你不用打开 Excel 也知道结果
    success_count = df[df["status"] == "success"].shape[0]
    error_count = df[df["status"] == "error"].shape[0]
    print(f"\n📊 结果摘要：")
    print(f"   成功 {success_count} 条，失败 {error_count} 条")
    print(f"   总 Token 消耗：{total_tokens}")  # 用 concat 之前算好的值
    # print(df)
    pass


# ── 主流程 ──────────────────────────────────────────────
# 重点：主流程只负责"调用顺序"，不包含任何业务逻辑。
# 这种"把细节关在函数里，主流程只当调度员"的结构——就是 Day 4 教的多函数串联。
if __name__ == "__main__":
    print("=" * 50)
    print("Day 14 综合练习：调 API → 存 Excel")
    print("=" * 50)

    # 第 1 步：构造问题
    questions = build_questions()
    print(f"\n共 {len(questions)} 个问题准备就绪\n")

    # 第 2-3 步：批量调 API
    results = batch_call(questions)

    # 第 4 步：存 Excel
    save_to_excel(results)
    print(f"\n✅ 完成！结果已保存到 api_results.xlsx")

