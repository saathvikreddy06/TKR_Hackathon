import json
from pathlib import Path


DATA_FILE = Path("data/real_bis_standards.json")


def main():
    print("Loading BIS dataset...")

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    print("\nDataset loaded successfully!")
    print("Python type:", type(data).__name__)

    if isinstance(data, list):
        print("Number of records:", len(data))

        if len(data) > 0:
            first_record = data[0]

            print("\nFirst record:")
            print(json.dumps(first_record, indent=2, ensure_ascii=False))

            print("\nFields:")
            for field in first_record.keys():
                print("-", field)

    elif isinstance(data, dict):
        print("Top-level keys:")

        for key in data.keys():
            print("-", key)

        print("\nDataset preview:")
        print(json.dumps(data, indent=2, ensure_ascii=False)[:5000])

    else:
        print("Unexpected dataset structure.")


if __name__ == "__main__":
    main()