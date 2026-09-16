import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

files = [
    "data/normalized/standards/bis_standards_master.json",
    "data/normalized/standards/standard_qco_links.json",
    "data/normalized/standards/standard_lab_test_links.json",
    "data/normalized/labs/bis_lims_labs.json",
    "data/normalized/labs/bis_lims_tests.json",
]

for relative in files:
    path = ROOT / relative

    print("\n===", relative, "===")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print("Type:", type(data).__name__)

    if isinstance(data, dict):
        print("Keys:", list(data.keys()))

        for key, value in data.items():
            if isinstance(value, list):
                print("List key:", key)
                print("Count:", len(value))

                if value:
                    print(
                        "Sample:",
                        json.dumps(
                            value[0],
                            ensure_ascii=False
                        )[:1500]
                    )
                break
    elif isinstance(data, list):
        print("Count:", len(data))

        if data:
            print(
                "Sample:",
                json.dumps(
                    data[0],
                    ensure_ascii=False
                )[:1500]
            )