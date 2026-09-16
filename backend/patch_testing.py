from pathlib import Path

p = Path("app/hybrid_retrieval.py")
s = p.read_text(encoding="utf-8")

marker = "    def lab_search(self, is_numbers, limit=20):"

method = '''    def test_search(self, is_numbers, limit=50):
        results = []
        seen = set()

        for number in is_numbers:
            for test in self.tests_by_is.get(number, []):
                key = (
                    test.get("indian_standard_no"),
                    test.get("product"),
                    test.get("designation"),
                    test.get("clause_raw")
                )

                if key in seen:
                    continue

                seen.add(key)

                results.append({
                    "standard_number": test.get("indian_standard_no"),
                    "product": test.get("product"),
                    "designation": test.get("designation"),
                    "clause": test.get("clause_raw"),
                    "exclusion": test.get("exclusion"),
                    "testing_charge": test.get("testing_charge"),
                    "testing_charge_raw": test.get("testing_charge_raw"),
                    "effective_date": test.get("effective_date"),
                    "remark": test.get("remark"),
                    "lab_code": test.get("lab_code"),
                    "lab_name": test.get("lab_name"),
                    "scope_url": test.get("scope_url"),
                    "source": "BIS LIMS"
                })

                if len(results) >= limit:
                    return results

        return results

'''

if "def test_search(self, is_numbers, limit=50):" in s:
    print("TEST SEARCH ALREADY EXISTS")
else:
    if marker not in s:
        raise SystemExit("MARKER NOT FOUND")

    s = s.replace(marker, method + marker, 1)
    p.write_text(s, encoding="utf-8")
    print("PATCHED TEST SEARCH")