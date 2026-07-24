import pytest
import pandas as pd
from pathlib import Path

@pytest.fixture(scope="module")
def load_excel():

    excel_path = Path(__file__).parent/"api_results.xlsx"

    if not excel_path.exists():
        pytest.fail(f"找不到excel路径，请先生成excel")
    df = pd.read_excel(excel_path)

    return df