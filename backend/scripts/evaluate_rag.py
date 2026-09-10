import json
import time
from pathlib import Path

import requests


API_URL = "http://127.0.0.1:8000/api/search"

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
    Check whether the retrieved result contains
    the expected BIS standard number and year.
    """

    if not expected_is:
        return False

    expected = normalize(expected_is)

    standard_number = normalize(
        result.get("standard_number")
    )

    year = normalize(
        result.get("year")
    )

    if ":" in expected:

        expected_number, expected_year = expected.split(
            ":", 1
        )

        return (
            normalize(expected_number) == standard_number
            and normalize(expected_year) == year
        )

    return expected == standard_number


def evaluate_test_case(test_case):

    query = test_case["query"]

    expected_is = test_case.get("expected_is")
    expected_scheme = test_case.get("expected_scheme")

    start = time.perf_counter()

    try:

        response = requests.post(
            API_URL,
            json={
                "query": query,
                "limit": 5
            },
            timeout=60
        )

        elapsed = time.perf_counter() - start

        # API returned an error
        if response.status_code != 200:

            return {
                "id": test_case["id"],
                "question": query,
                "status": "API_ERROR",
                "http_status": response.status_code,
                "error_response": response.text,
                "latency_seconds": round(elapsed, 3)
            }

        data = response.json()

        results = data.get(
            "retrieved_results",
            []
        )

        sources = data.get(
            "sources",
            []
        )

        # ------------------------------------------
        # Retrieval evaluation
        # ------------------------------------------

        retrieved_correct = any(
            standard_matches(
                result,
                expected_is
            )
            for result in results
        )

        # ------------------------------------------
        # Generated answer evaluation
        # ------------------------------------------

        generated_answer = normalize(
            data.get("answer", "")
        )

        answer_mentions_expected = False

        if expected_is:

            expected_number = normalize(
                expected_is.split(":")[0]
            )

            answer_mentions_expected = (
                expected_number
                in generated_answer
            )

        # ------------------------------------------
        # Scheme evaluation
        # ------------------------------------------

        scheme_correct = True

        if expected_scheme:

            scheme_correct = any(
                normalize(
                    source.get("scheme")
                )
                == normalize(expected_scheme)

                for source in sources

                if standard_matches(
                    source,
                    expected_is
                )
            )

        return {
            "id": test_case["id"],
            "question": query,
            "expected_is": expected_is,
            "expected_scheme": expected_scheme,
            "retrieval_correct": retrieved_correct,
            "answer_mentions_expected": answer_mentions_expected,
            "scheme_correct": scheme_correct,
            "latency_seconds": round(elapsed, 3),
            "status": (
                "PASS"
                if retrieved_correct
                else "FAIL"
            )
        }

    except Exception as e:

        elapsed = time.perf_counter() - start

        return {
            "id": test_case["id"],
            "question": query,
            "status": "ERROR",
            "error": str(e),
            "latency_seconds": round(elapsed, 3)
        }


def main():

    print("=" * 60)
    print("StandIQ RAG Evaluation")
    print("=" * 60)

    # ------------------------------------------
    # Check benchmark file
    # ------------------------------------------

    if not BENCHMARK_FILE.exists():

        print()
        print(
            "ERROR: Benchmark file not found:"
        )

        print(BENCHMARK_FILE)

        return

    # ------------------------------------------
    # Load benchmark
    # ------------------------------------------

    with open(
        BENCHMARK_FILE,
        "r",
        encoding="utf-8"
    ) as file:

        benchmark = json.load(file)

    print(
        f"Loaded {len(benchmark)} test cases"
    )

    print()

    results = []

    # ------------------------------------------
    # Run evaluation
    # ------------------------------------------

    for index, test_case in enumerate(
        benchmark,
        start=1
    ):

        query = test_case["query"]

        print(
            f"[{index}/{len(benchmark)}] "
            f"{test_case['id']} - "
            f"{query}"
        )

        result = evaluate_test_case(
            test_case
        )

        results.append(result)

        print(
            f"    Status: {result['status']} "
            f"| Retrieval: "
            f"{result.get('retrieval_correct', '-')}"
            f" | Time: "
            f"{result['latency_seconds']}s"
        )

        # Print actual API error
        if result["status"] in [
            "API_ERROR",
            "ERROR"
        ]:

            print(
                "    Details: "
                f"{result.get(
                    'error_response',
                    result.get(
                        'error',
                        'Unknown error'
                    )
                )}"
            )

    # ------------------------------------------
    # Calculate metrics
    # ------------------------------------------

    total = len(results)

    retrieval_correct = sum(
        1
        for result in results
        if result.get(
            "retrieval_correct"
        ) is True
    )

    answer_correct = sum(
        1
        for result in results
        if result.get(
            "answer_mentions_expected"
        ) is True
    )

    scheme_correct = sum(
        1
        for result in results
        if result.get(
            "scheme_correct"
        ) is True
    )

    valid_results = [
        result
        for result in results
        if "latency_seconds" in result
    ]

    avg_latency = (
        sum(
            result["latency_seconds"]
            for result in valid_results
        )
        / len(valid_results)
        if valid_results
        else 0
    )

    # ------------------------------------------
    # Print summary
    # ------------------------------------------

    print()

    print("=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)

    print(
        f"Total test cases:       "
        f"{total}"
    )

    if total > 0:

        print(
            f"Correct retrieval:      "
            f"{retrieval_correct}/{total} "
            f"({retrieval_correct / total * 100:.1f}%)"
        )

        print(
            f"Answer mentions IS:     "
            f"{answer_correct}/{total} "
            f"({answer_correct / total * 100:.1f}%)"
        )

        print(
            f"Correct scheme:         "
            f"{scheme_correct}/{total} "
            f"({scheme_correct / total * 100:.1f}%)"
        )

    print(
        f"Average latency:        "
        f"{avg_latency:.2f}s"
    )

    # ------------------------------------------
    # Save detailed results
    # ------------------------------------------

    output_file = (
        Path(__file__).resolve().parent
        / "evaluation_results.json"
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
        "Detailed results saved to:"
    )

    print(output_file)

    print("=" * 60)


if __name__ == "__main__":
    main()
