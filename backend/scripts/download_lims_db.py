#!/usr/bin/env python3
"""
download_lims_db.py — Download the production LIMS SQLite database from
external object storage during the Render build step.

Environment variables required:
  LIMS_DB_URL      — Full HTTPS URL to the SQLite file
                     (e.g. https://storage.example.com/lims/structured_lims_lookup.sqlite3)
  LIMS_DB_SHA256   — SHA-256 hex digest of the file for integrity verification

Optional:
  LIMS_DB_PATH     — Override the local destination path
                     Default: backend/data/processed/structured_lims_lookup.sqlite3

Behaviour:
  - If the destination file already exists and its SHA-256 matches LIMS_DB_SHA256,
    the download is skipped (idempotent restarts are safe).
  - The file is streamed in 8 MB chunks so it does not require the full file to
    fit in memory before writing.
  - If LIMS_DB_URL is not set, the script exits with code 0 and a warning so that
    local developer builds that already have the file are not broken.
  - If the downloaded file's checksum does not match, the script deletes the corrupt
    file and exits with code 1 so the Render build fails immediately rather than
    silently deploying broken LIMS data.
"""

from __future__ import annotations

import hashlib
import os
import sys
import urllib.request
from pathlib import Path


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LIMS_DB_URL: str | None = os.environ.get("LIMS_DB_URL", "").strip() or None
LIMS_DB_SHA256: str | None = os.environ.get("LIMS_DB_SHA256", "").strip() or None

# Resolve destination path relative to this script's parent (backend root)
_DEFAULT_DEST = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "processed"
    / "structured_lims_lookup.sqlite3"
)

LIMS_DB_PATH = Path(
    os.environ.get("LIMS_DB_PATH", "").strip() or str(_DEFAULT_DEST)
)

CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sha256_of_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def file_matches_checksum(path: Path, expected: str | None) -> bool:
    """Return True if the file exists and its SHA-256 matches expected."""
    if not path.is_file():
        return False
    if not expected:
        # No checksum provided; accept whatever exists.
        return True
    actual = sha256_of_file(path)
    return actual.lower() == expected.lower()


def download_file(url: str, dest: Path) -> None:
    """Stream-download url to dest, updating a progress counter."""
    dest.parent.mkdir(parents=True, exist_ok=True)

    tmp_path = dest.with_suffix(".tmp")
    try:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "StandIQ-Render-build/1.0"},
        )
        with (
            urllib.request.urlopen(request) as response,
            tmp_path.open("wb") as out_fh,
        ):
            total_str = response.headers.get("Content-Length", "")
            total = int(total_str) if total_str.isdigit() else None
            downloaded = 0
            while True:
                chunk = response.read(CHUNK_SIZE)
                if not chunk:
                    break
                out_fh.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = downloaded * 100 // total
                    print(
                        f"\r  Downloading… {downloaded / 1_048_576:.1f} MB"
                        f" / {total / 1_048_576:.1f} MB ({pct}%)",
                        end="",
                        flush=True,
                    )
                else:
                    print(
                        f"\r  Downloading… {downloaded / 1_048_576:.1f} MB",
                        end="",
                        flush=True,
                    )
        print()  # newline after progress
        tmp_path.rename(dest)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=== LIMS database download ===")
    print(f"Destination : {LIMS_DB_PATH}")

    if not LIMS_DB_URL:
        print(
            "LIMS_DB_URL is not set. "
            "Skipping download (expected on developer machines that "
            "already have the file or that use the Firestore LIMS fallback)."
        )
        # Exit 0 — do not break local dev builds.
        return 0

    print(f"Source URL  : {LIMS_DB_URL}")
    if LIMS_DB_SHA256:
        print(f"Expected SHA: {LIMS_DB_SHA256}")
    else:
        print("LIMS_DB_SHA256 is not set — checksum verification will be skipped.")

    # Check if the file is already present and intact
    if file_matches_checksum(LIMS_DB_PATH, LIMS_DB_SHA256):
        size_mb = LIMS_DB_PATH.stat().st_size / 1_048_576
        print(
            f"File already exists and checksum matches ({size_mb:.1f} MB). "
            "Skipping download."
        )
        return 0

    # Download
    print("Downloading LIMS database…")
    try:
        download_file(LIMS_DB_URL, LIMS_DB_PATH)
    except Exception as exc:
        print(f"ERROR: Download failed: {exc}", file=sys.stderr)
        return 1

    # Verify checksum after download
    if LIMS_DB_SHA256:
        print("Verifying checksum…")
        actual = sha256_of_file(LIMS_DB_PATH)
        if actual.lower() != LIMS_DB_SHA256.lower():
            print(
                f"ERROR: Checksum mismatch!\n"
                f"  Expected : {LIMS_DB_SHA256.lower()}\n"
                f"  Actual   : {actual}",
                file=sys.stderr,
            )
            LIMS_DB_PATH.unlink(missing_ok=True)
            return 1
        print(f"Checksum verified: {actual}")
    else:
        print("Checksum verification skipped (LIMS_DB_SHA256 not set).")

    size_mb = LIMS_DB_PATH.stat().st_size / 1_048_576
    print(f"LIMS database ready: {LIMS_DB_PATH} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
