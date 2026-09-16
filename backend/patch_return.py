from pathlib import Path

p = Path("app/hybrid_retrieval.py")
s = p.read_text(encoding="utf-8")

old = '''        return {
            "query": query,
            "intent": intent,
            "is_numbers": is_numbers,
            "semantic": semantic,
            "exact_standards": exact,
            "qco": qco,
            "labs": labs
        }
'''

new = '''        return {
            "query": query,
            "intent": intent,
            "is_numbers": is_numbers,
            "semantic": semantic,
            "exact_standards": exact,
            "qco": qco,
            "labs": labs,
            "tests": tests
        }
'''

if old not in s:
    print("OLD RETURN BLOCK NOT FOUND")
else:
    s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")
    print("RETURN BLOCK PATCHED")