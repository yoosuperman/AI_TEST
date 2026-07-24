import os, requests
from dotenv import load_dotenv
load_dotenv()

resp = requests.post(
    f"{os.getenv("dashscope_base_url")}/chat/completions",
    headers={"Authorization": f"Bearer {os.getenv('DASHSCOPE_API_KEY')}"},
    json={"model": "qwen-turbo", "messages": [{"role": "user", "content": "说'OK'"}]},
    timeout=15
)
print(resp.status_code)