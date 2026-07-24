import pytest
import pandas as pd




@pytest.mark.parametrize("label,expected_min,condition",[
    ("总行数 >= 20", 20, None),                         # 至少 20 条
    ("成功条数 >= 20", 20, "status == 'success'"),       # 至少 20 条成功
    ("流式条数 == 5", 5, "stream == True"),              # 正好 5 条流式
    ("非流式条数 == 15", 15, "stream == False"),         # 正好 15 条非流式
])

def test_row_counts(load_excel,label,expected_min,condition):

    df = load_excel
    if condition is None:
        count = len(df)
        count -= 1
        print(f"整体len为{count=}，类型为{type(df)}")
    else:
        # 重点：df.query() 是 pandas 的筛选方法，比 df[df[...]] 更简洁
        count = len(df.query(condition))

        # assert 失败时 pytest 会打印 label 和实际值，方便排错
    assert count == expected_min, f"{label}：期望 >= {expected_min}，实际 {count}"



def test_required_columns(load_excel):
    """验证 Excel 包含所有必要列。"""

    df = load_excel
    required = ["question", "answer", "tokens", "stream", "status", "http_status"]

    for col in required:
        assert col in df.columns, f"缺少列：{col}"
    assert df.shape[1] == len(required)


def test_success_status_code_is_200(load_excel):
    """验证所有成功行的 HTTP 状态码都是 200。"""

    df = load_excel
    success_rows = df[df["status"] == "success"]

    # 去掉统计行（question 为 '【统计】' 的那一行），它不是真正的 API 调用
    success_rows = success_rows[success_rows["question"] != "【统计】"]

    # http_status 在 Excel 里读出来可能是 float 或 int，统一转成 int 比较
    non_200 = success_rows[success_rows["http_status"] != 200]
    assert len(non_200) == 0, (
        f"有 {len(non_200)} 条 status='success' 但 http_status 不是 200：\n"
        f"行号: {non_200.index.tolist()}\n"
        f"详情: {non_200[['question', 'http_status']].to_dict('records')}"
    )

def test_answers_not_empty(load_excel):
    """验证成功行的 answer 列不为空。

    重点：只检查 status=="success" 的行——失败行的 answer 可能是空字符串。
    如果不加这个筛选，assert 会错误地因为失败行而挂掉。
    """

    df = load_excel
    # 取出所有成功的行（重点：这一步筛选，Day 13 教的 pandas 条件筛选）
    success_rows = df[df["status"] == "success"]

    # 这些行的 answer 不能为空
    empty_answers = success_rows[success_rows["answer"].isna() | (success_rows["answer"] == "")]
    assert len(empty_answers) == 0, (
        f"有 {len(empty_answers)} 条成功的行 answer 为空：\n"
        f"{empty_answers['question'].tolist()}"
    )

def test_token_usage(load_excel):
    """验证成功的 API 调用消耗了 Token。

    重点：如果一条 API 调用成功了（status=="success"）但 total_tokens=0，
    说明 call_one_api() 的 token 提取逻辑有问题——可能用了非流式的路径读流式响应，
    或用了 .message 而不是 .delta。
    """
    df = load_excel
    success_rows = df[df["status"] == "success"]

    # 成功的调用必须消耗了 token
    zero_token_success = success_rows[success_rows["tokens"] == 0]
    assert len(zero_token_success) == 0, (
        f"有 {len(zero_token_success)} 条成功调用 tokens=0，"
        f"可能是 token 提取逻辑有 bug：\n"
        f"{zero_token_success['question'].tolist()}"
    )

    # 总 token 消耗至少 > 0
    assert df["tokens"].sum() > 0, "总 Token 消耗为 0，不正常"


def test_status_distribution(load_excel):
    """验证整体状态分布合理——大部分应该是 success。

    重点：不对 status 做 100% 的硬性断言（网络抖动可能导致偶发失败），
    而是验证"成功率 >= 75%"——留 25% 的容错空间。
    """
    df = load_excel
    total = len(df)
    success_count = df[df["status"] == "success"].shape[0]

    success_rate = success_count / total if total > 0 else 0
    assert success_rate >= 0.75, (
        f"成功率过低：{success_rate:.1%}（{success_count}/{total}）"
    )