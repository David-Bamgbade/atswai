import json

path = "data/extracted/papers/paper_02_economics.json"

with open(path, "r", encoding="utf-8") as file:
    data = json.load(file)

print(json.dumps(data, indent=2, ensure_ascii=False)[:12000])