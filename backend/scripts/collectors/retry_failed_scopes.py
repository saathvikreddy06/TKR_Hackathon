import json
import time
from datetime import datetime, timezone
from pathlib import Path

from lims_scopes import (
    fetch_page,
    parse_scope,
    save_raw,
    save_json,
    INPUT_FILE,
    OUTPUT_FILE,
    MANIFEST_FILE,
    RAW_DIR,
    HEADERS,
    REQUEST_DELAY_SECONDS,
)

import requests


def main():

    print()
    print("=" * 60)
    print("BIS LIMS FAILED SCOPE RETRY")
    print("=" * 60)
    print()

    if not OUTPUT_FILE.exists():
        raise FileNotFoundError(
            f"Scope output not found: {OUTPUT_FILE}"
        )

    data = json.loads(
        OUTPUT_FILE.read_text(
            encoding="utf-8"
        )
    )

    failures = data.get(
        "failures",
        []
    )

    existing_results = {
        item.get("lab_code"): item
        for item in data.get(
            "laboratories",
            []
        )
    }

    print(
        f"Failed labs to retry: {len(failures)}"
    )

    if not failures:
        print("Nothing to retry.")
        return

    new_failures = []

    successful_retries = 0

    with requests.Session() as session:

        for index, failure in enumerate(
            failures,
            start=1,
        ):

            lab_code = failure.get(
                "lab_code"
            )

            lab_name = failure.get(
                "lab_name"
            )

            scope_url = failure.get(
                "scope_url"
            )

            print(
                f"[{index}/{len(failures)}] "
                f"{lab_code} - {lab_name}"
            )

            if not scope_url:
                new_failures.append(failure)
                continue

            try:

                time.sleep(
                    REQUEST_DELAY_SECONDS * 2
                )

                html = fetch_page(
                    session,
                    scope_url,
                    max_retries=5,
                )

                # Reconstruct the laboratory object
                # from the original recognized-lab dataset.
                source_data = json.loads(
                    INPUT_FILE.read_text(
                        encoding="utf-8"
                    )
                )

                matching_lab = next(
                    (
                        lab
                        for lab in source_data[
                            "laboratories"
                        ]
                        if lab.get(
                            "lab_code"
                        ) == lab_code
                    ),
                    None,
                )

                if matching_lab is None:
                    raise ValueError(
                        "Original laboratory record "
                        "not found"
                    )

                raw_path = save_raw(
                    html,
                    lab_code,
                )

                scope_data = parse_scope(
                    html,
                    matching_lab,
                )

                scope_data[
                    "retrieved_at"
                ] = (
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                scope_data[
                    "raw_file"
                ] = str(raw_path)

                existing_results[
                    lab_code
                ] = scope_data

                successful_retries += 1

                print("    RETRY OK")

            except Exception as exc:

                print(
                    f"    STILL FAILED: {exc}"
                )

                new_failures.append(
                    {
                        **failure,
                        "last_retry_error": str(
                            exc
                        ),
                    }
                )

    final_laboratories = list(
        existing_results.values()
    )

    output = {
        **data,
        "source": {
            **data.get(
                "source",
                {}
            ),
            "updated_at": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
        },
        "statistics": {
            "input_laboratories": 431,
            "successful": len(
                final_laboratories
            ),
            "failed": len(
                new_failures
            ),
            "total": 431,
        },
        "laboratories": final_laboratories,
        "failures": new_failures,
    }

    save_json(
        output,
        OUTPUT_FILE,
    )

    manifest = {
        "document_id": (
            "BIS_LIMS_RECOGNIZED_LAB_SCOPES"
        ),
        "source_id": "bis_lims",
        "source_type": "BIS_OFFICIAL",
        "document_type": "LABORATORY_SCOPE",
        "lab_category": "RECOGNIZED",
        "retrieved_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "status": (
            "completed"
            if not new_failures
            else "completed_with_errors"
        ),
        "total": 431,
        "successful": len(
            final_laboratories
        ),
        "failed": len(
            new_failures
        ),
        "successful_retries": (
            successful_retries
        ),
        "parser_version": "1.1",
    }

    save_json(
        manifest,
        MANIFEST_FILE,
    )

    print()
    print("=" * 60)
    print("RETRY COMPLETE")
    print("=" * 60)
    print(
        f"Previously failed : {len(failures)}"
    )
    print(
        f"Recovered          : "
        f"{successful_retries}"
    )
    print(
        f"Still failed       : "
        f"{len(new_failures)}"
    )
    print(
        f"Total successful   : "
        f"{len(final_laboratories)}"
    )
    print()


if __name__ == "__main__":
    main()