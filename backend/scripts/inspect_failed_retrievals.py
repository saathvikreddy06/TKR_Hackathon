import json


with open("data/real_bis_standards.json", "r", encoding="utf-8") as f:
    data = json.load(f)


targets = [
    "IS 15298",
    "IS 15683"
]


for target in targets:

    print("\n" + "=" * 70)
    print(f"SEARCHING FOR: {target}")
    print("=" * 70)

    found = False

    for item in data:

        text = json.dumps(item, ensure_ascii=False)

        if target in text:

            found = True

            print(json.dumps(
                item,
                indent=2,
                ensure_ascii=False
            ))

    if not found:
        print(f"❌ {target} NOT FOUND")