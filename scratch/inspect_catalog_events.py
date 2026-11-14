import json

with open("dataset/catalog.json") as f:
    cat = json.load(f)

for v in cat["videos"]:
    print(f"{v['file_name']}: cat={v['category']}, sub={v['sub_category']}, leap={v['is_positive_leap']}")
