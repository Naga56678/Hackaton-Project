import requests

response = requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "gpt-oss:20b", "prompt": "Hello, how are you?"},
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode())
