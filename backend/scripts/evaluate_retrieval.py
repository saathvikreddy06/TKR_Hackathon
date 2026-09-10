import json
import time
from pathlib import Path

from app.retrieval import search_standards


BENCHMARK_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "evaluation_benchmarks.json"
)


def normalize(value):
    if value is None:
        return ""

    return str(value).strip().lower()


def standard_matches(result, expected_is):
    """
    Compare the complete BIS standard identity.

    Examples:
    IS 16046 (Part 2):2018
    IS 15885 (Part 2/Sec 13):2012
    IS 2553 (Part 1):2018
    IS 1786:2008
    """

    if not expected_is:
        return False

    expected = normalize(expected_is)

    result_number = normalize(
        result.get("standard_number")
    )

    result_part = normalize(
        result.get("part")
    )

    result_section = normalize(
        result.get("section")
    )

    result_year = normalize(
        result.get("year")
    )

    # --------------------------------------------------
    # Extract expected year
    # --------------------------------------------------

    if ":" in expected:

        expected_base, expected_year = expected.rsplit(":", 1)

        expected_base = expected_base.strip()
        expected_year = expected_year.strip()

    else:

        expected_base = expected
        expected_year = ""

    # --------------------------------------------------
    # Base standard number must match
    # --------------------------------------------------

    if result_number != expected_base.split("(")[0].strip():
        return False

    # --------------------------------------------------
    # Year must match when supplied
    # --------------------------------------------------

    if expected_year:

        if result_year != expected_year:
            return False

    # --------------------------------------------------
    # Extract Part / Section information
    # --------------------------------------------------

    expected_part = ""
    expected_section = ""

    if "(" in expected_base:

        details = expected_base[
            expected_base.find("("):
        ]

        details = details.replace("(", "").replace(")", "")

        # Example:
        # "Part 2"
        # "Part 2/Sec 13"

        if "/" in details:

            part_text, section_text = details.split(
                "/",
                1
            )

            expected_part = normalize(part_text)
            expected_section = normalize(section_text)

        else:

            expected_part = normalize(details)

    # --------------------------------------------------
    # Compare Part
    # --------------------------------------------------

    if expected_part:

        if expected_part != result_part:

            return False

    # --------------------------------------------------
    # Compare Section
    # --------------------------------------------------

    if expected_section:

        if expected_section != result_section:

            return False

    return True


def main():

    print("=" * 60)
    print("StandIQ Retrieval Evaluation")
    print("=" * 60)

    with open(
        BENCHMARK_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        benchmark = json.load(file)

    print(f"Loaded {len(benchmark)} test cases")
    print()

    results = []

    for index, test_case in enumerate(benchmark, start=1):

        test_id = test_case["id"]
        query = test_case["query"]
        expected_is = test_case.get("expected_is")
        expected_scheme = test_case.get("expected_scheme")
        out_of_scope = test_case.get("out_of_scope", False)

        print(
            f"[{index}/{len(benchmark)}] "
            f"{test_id} - {query}"
        )

        start = time.perf_counter()

        try:

            retrieved = search_standards(
                query=query,
                limit=10
            )

            elapsed = time.perf_counter() - start

            retrieval_correct = any(
                standard_matches(
                    result,
                    expected_is
                )
                for result in retrieved
            )

            scheme_correct = True

            if expected_scheme:

                scheme_correct = any(
                    standard_matches(
                        result,
                        expected_is
                    )
                    and normalize(
                        result.get("scheme")
                    ) == normalize(expected_scheme)

                    for result in retrieved
                )

            retrieved_numbers = [
                {
                    "standard_number": result.get("standard_number"),
                    "part": result.get("part"),
                    "section": result.get("section"),
                    "year": result.get("year")
                }
                for result in retrieved
            ]

            result = {
                "id": test_id,
                "query": query,
                "expected_is": expected_is,
                "expected_scheme": expected_scheme,
                "out_of_scope": out_of_scope,
                "retrieval_correct": retrieval_correct,
                "scheme_correct": scheme_correct,
                "retrieved": retrieved_numbers,
                "latency_seconds": round(elapsed, 3)
            }

            results.append(result)

            status = "PASS" if retrieval_correct else "FAIL"

            print(
                f"    {status} | "
                f"Expected: {expected_is} | "
                f"Retrieved: {retrieved_numbers[:3]} | "
                f"Time: {elapsed:.2f}s"
            )

        except Exception as e:

            elapsed = time.perf_counter() - start

            print(
                f"    ERROR | "
                f"{str(e)}"
            )

            results.append({
                "id": test_id,
                "query": query,
                "expected_is": expected_is,
                "expected_scheme": expected_scheme,
                "out_of_scope": out_of_scope,
                "retrieval_correct": False,
                "scheme_correct": False,
                "error": str(e),
                "latency_seconds": round(elapsed, 3)
            })

    # ------------------------------------------------
    # Metrics
    # ------------------------------------------------

    in_scope = [
        result
        for result in results
        if not result["out_of_scope"]
    ]

    retrieval_correct = sum(
        result["retrieval_correct"]
        for result in in_scope
    )

    scheme_correct = sum(
        result["scheme_correct"]
        for result in in_scope
    )

    total = len(in_scope)

    avg_latency = (
        sum(
            result["latency_seconds"]
            for result in results
        ) / len(results)
        if results
        else 0
    )

    print()
    print("=" * 60)
    print("RETRIEVAL EVALUATION SUMMARY")
    print("=" * 60)

    print(f"Total test cases:    {len(results)}")
    print(f"In-scope cases:      {total}")

    if total:

        print(
            f"Correct retrieval:   "
            f"{retrieval_correct}/{total} "
            f"({retrieval_correct / total * 100:.1f}%)"
        )

        print(
            f"Correct scheme:      "
            f"{scheme_correct}/{total} "
            f"({scheme_correct / total * 100:.1f}%)"
        )

    print(
        f"Average latency:     "
        f"{avg_latency:.2f}s"
    )

    print()

    failed = [
        result
        for result in in_scope
        if not result["retrieval_correct"]
    ]

    print(
        f"Failed retrievals: {len(failed)}"
    )

    for result in failed:

        print(
            f"  {result['id']} "
            f"→ expected {result['expected_is']}"
        )

        print(
            f"     Retrieved: "
            f"{result.get('retrieved', [])}"
        )

    # ------------------------------------------------
    # Save results
    # ------------------------------------------------

    output_file = (
        Path(__file__).resolve().parent
        / "retrieval_evaluation_results.json"
    )

    with open(
        output_file,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=2,
            ensure_ascii=False
        )

    print()
    print(
        f"Results saved to: {output_file}"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()