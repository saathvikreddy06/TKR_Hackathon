from pathlib import Path

p = Path("app/hybrid_retrieval.py")
s = p.read_text(encoding="utf-8")

marker = '        elif intent == "standard":'

branch = '''        elif intent == "testing":
            exact = self.exact_standards(
                is_numbers
            )

            labs = self.test_search(
                is_numbers,
                50
            )

'''

if 'elif intent == "testing":' in s:
    print("TESTING BRANCH ALREADY EXISTS")
else:
    if marker not in s:
        raise SystemExit("STANDARD MARKER NOT FOUND")

    s = s.replace(marker, branch + marker, 1)
    p.write_text(s, encoding="utf-8")
    print("PATCHED TESTING BRANCH")