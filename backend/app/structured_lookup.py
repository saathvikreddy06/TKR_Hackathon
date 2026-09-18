import json
import os
import re
import sqlite3
from pathlib import Path

import importlib


ijson = importlib.import_module("ijson")


class StructuredLookupIndex:
    """Indexed lookups over the existing normalized BIS LIMS data."""

    def __init__(self, tests_path, labs_path, index_path):
        self.tests_path = Path(tests_path)
        self.labs_path = Path(labs_path)
        self.index_path = Path(index_path)
        self._ready = False
        self.error = None

    @staticmethod
    def identifier_keys(value):
        if value is None:
            return set()

        text = str(value).upper().strip()
        text = re.sub(r"\bI\.S\.\b", "IS", text)
        text = re.sub(r"\bIS\s*/\s*IEC\b", "IS", text)
        text = re.sub(r"\bIEC\b", "IS", text)
        text = re.sub(r"\bIS\b", " ", text)

        match = re.search(r"(\d{3,6})", text)
        if not match:
            return set()

        number = match.group(1)
        tail = text[match.end():]
        part_match = re.search(r"(?:PART|PT)\s*[-./]?\s*(\d{1,3})", tail)
        year_match = re.search(r"(?:^|[^0-9])(\d{4})(?:\D|$)", tail)
        part = part_match.group(1) if part_match else None
        year = year_match.group(1) if year_match else None

        keys = {number}
        if part:
            keys.add(f"{number}:{part}")
        if year:
            keys.add(f"{number}:{year}")
        if part and year:
            keys.add(f"{number}:{part}:{year}")
        return keys

    @classmethod
    def primary_key(cls, value):
        keys = cls.identifier_keys(value)
        if not keys:
            return ""
        return sorted(keys, key=lambda item: (item.count(":"), len(item)), reverse=True)[0]

    def _source_signature(self):
        paths = (self.tests_path, self.labs_path)
        return "|".join(
            f"{path}:{path.stat().st_mtime_ns}:{path.stat().st_size}"
            for path in paths
            if path.exists()
        )

    def _is_current(self, connection):
        try:
            row = connection.execute(
                "SELECT value FROM metadata WHERE key = 'source_signature'"
            ).fetchone()
        except sqlite3.OperationalError:
            return False
        return bool(row and row[0] == self._source_signature())

    def _open(self):
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(str(self.index_path), timeout=60)

    def _create_schema(self, connection):
        connection.executescript(
            """
            DROP TABLE IF EXISTS tests;
            DROP TABLE IF EXISTS laboratories;
            DROP TABLE IF EXISTS metadata;
            CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE tests (
                test_id TEXT PRIMARY KEY,
                standard_key TEXT NOT NULL,
                base_key TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE laboratories (
                lab_code TEXT PRIMARY KEY,
                payload TEXT NOT NULL
            );
            CREATE INDEX tests_standard_key_idx ON tests (standard_key);
            CREATE INDEX tests_base_key_idx ON tests (base_key);
            """
        )

    def _load_laboratories(self, connection):
        if not self.labs_path.exists():
            return

        data = json.loads(self.labs_path.read_text(encoding="utf-8"))
        rows = data if isinstance(data, list) else data.get("laboratories", [])
        values = []
        for item in rows:
            if not isinstance(item, dict) or not item.get("lab_code"):
                continue
            values.append((str(item["lab_code"]), json.dumps(item, ensure_ascii=False)))
        connection.executemany(
            "INSERT OR REPLACE INTO laboratories (lab_code, payload) VALUES (?, ?)",
            values,
        )

    def _build(self, connection):
        self._create_schema(connection)
        self._load_laboratories(connection)

        if not self.tests_path.exists():
            raise FileNotFoundError(str(self.tests_path))

        batch = []
        with self.tests_path.open("rb") as file:
            for item in ijson.items(file, "item"):
                if not isinstance(item, dict):
                    continue

                standard = (
                    item.get("indian_standard_no")
                    or item.get("standard_number")
                    or item.get("is_number")
                    or item.get("standard")
                )
                keys = self.identifier_keys(standard)
                if not keys:
                    continue

                primary = self.primary_key(standard)
                base = min(keys, key=lambda key: (key.count(":"), len(key)))
                test_id = str(item.get("test_id") or item.get("record_hash") or f"{primary}:{len(batch)}")
                payload = {
                    "lab_code": item.get("lab_code"),
                    "lab_name": item.get("lab_name"),
                    "indian_standard_no": standard,
                    "standard_number": standard,
                    "product": item.get("product"),
                    "designation": item.get("designation"),
                    "clause_raw": item.get("clause_raw"),
                    "exclusion": item.get("exclusion"),
                    "testing_charge": item.get("testing_charge"),
                    "testing_charge_raw": item.get("testing_charge_raw"),
                    "effective_date": item.get("effective_date"),
                    "remark": item.get("remark"),
                    "scope_id": item.get("scope_id"),
                    "scope_url": item.get("scope_url"),
                    "capability_id": item.get("capability_id"),
                    "source": item.get("source") or "BIS_LIMS",
                    "test_id": item.get("test_id"),
                }
                batch.append((test_id, primary, base, json.dumps(payload, ensure_ascii=False, default=str)))

                if len(batch) >= 2000:
                    connection.executemany(
                        "INSERT OR REPLACE INTO tests (test_id, standard_key, base_key, payload) VALUES (?, ?, ?, ?)",
                        batch,
                    )
                    batch.clear()

        if batch:
            connection.executemany(
                "INSERT OR REPLACE INTO tests (test_id, standard_key, base_key, payload) VALUES (?, ?, ?, ?)",
                batch,
            )

        connection.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES ('source_signature', ?)",
            (self._source_signature(),),
        )
        connection.commit()

    def _ensure_ready(self):
        if self._ready:
            return True

        try:
            connection = self._open()
            try:
                if not self._is_current(connection):
                    self._build(connection)
            finally:
                connection.close()
            self._ready = True
            self.error = None
            return True
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            print(f"Structured LIMS index error: {self.error}")
            return False

    @staticmethod
    def _decode_rows(rows):
        return [json.loads(row[0]) for row in rows]

    def lookup(self, identifiers, test_limit=50, lab_limit=20):
        if not self._ensure_ready():
            return {"status": "error", "error": self.error, "tests": [], "laboratories": []}

        keys = set()
        for identifier in identifiers:
            keys.update(self.identifier_keys(identifier))
        if not keys:
            return {"status": "not_found", "tests": [], "laboratories": []}

        placeholders = ",".join("?" for _ in keys)
        connection = self._open()
        try:
            rows = connection.execute(
                f"SELECT payload FROM tests WHERE standard_key IN ({placeholders}) OR base_key IN ({placeholders}) LIMIT ?",
                tuple(keys) + tuple(keys) + (max(int(test_limit), 1),),
            ).fetchall()
            tests = self._decode_rows(rows)

            lab_codes = []
            seen_codes = set()
            for item in tests:
                code = item.get("lab_code")
                if code and code not in seen_codes:
                    seen_codes.add(code)
                    lab_codes.append(code)
                if len(lab_codes) >= lab_limit:
                    break

            laboratories = []
            if lab_codes:
                lab_placeholders = ",".join("?" for _ in lab_codes)
                lab_rows = connection.execute(
                    f"SELECT payload FROM laboratories WHERE lab_code IN ({lab_placeholders})",
                    tuple(lab_codes),
                ).fetchall()
                lab_by_code = {
                    item.get("lab_code"): item
                    for item in (json.loads(row[0]) for row in lab_rows)
                }
                for code in lab_codes:
                    lab = dict(lab_by_code.get(code) or {})
                    matching = next((test for test in tests if test.get("lab_code") == code), {})
                    lab.update({
                        "standard_number": matching.get("standard_number"),
                        "product": matching.get("product"),
                        "capability": matching.get("designation") or matching.get("product"),
                        "relevant_test": matching.get("clause_raw"),
                        "source": matching.get("source") or "BIS_LIMS",
                        "match_type": "lims_lab",
                    })
                    laboratories.append(lab)

            for item in tests:
                item["match_type"] = "lims_test"

            return {
                "status": "supported" if tests or laboratories else "not_found",
                "tests": tests,
                "laboratories": laboratories,
            }
        finally:
            connection.close()
