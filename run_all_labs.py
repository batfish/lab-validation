#!/usr/bin/env python3
"""
Script to run validation tests across all available labs.

This script discovers all lab directories in the snapshots folder and runs
the validation test suite for each lab sequentially. It provides a summary
of results at the end.
"""

import subprocess
import sys
import time
from pathlib import Path


def discover_labs() -> list[str]:
    """Discover all available lab directories in the snapshots folder."""
    snapshots_dir = Path(__file__).parent / "snapshots"
    labs = []

    for path in snapshots_dir.iterdir():
        if path.is_dir() and not path.name.startswith("."):
            # Check if this directory has the required host_nos.txt file
            host_nos_file = path / "show" / "host_nos.txt"
            if host_nos_file.exists():
                labs.append(path.name)

    return sorted(labs)


def run_lab_tests(
    lab_name: str, verbose: bool = False
) -> tuple[bool, str, dict[str, int]]:
    """
    Run tests for a single lab.

    Returns (success, output, stats) where stats contains test counts.
    """
    cmd = ["pytest", "lab_tests/test_labs.py", f"--labname={lab_name}", "--tb=no"]
    if not verbose:
        cmd.append("-q")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout per lab
        )

        # Parse pytest output for statistics
        stats = {"passed": 0, "failed": 0, "xfailed": 0, "skipped": 0}

        # Look for pytest summary line like "10 passed, 1 xfailed in 4.37s"
        output_text = result.stdout + result.stderr
        lines = output_text.split("\n")

        # Look for the summary line at the end
        for line in reversed(lines):
            if any(
                keyword in line
                for keyword in [" passed", " failed", " xfailed", " skipped"]
            ):
                # Parse the summary line
                import re

                # Match patterns like "10 passed, 1 xfailed in 4.37s"
                passed_match = re.search(r"(\d+) passed", line)
                failed_match = re.search(r"(\d+) failed", line)
                xfailed_match = re.search(r"(\d+) xfailed", line)
                skipped_match = re.search(r"(\d+) skipped", line)

                if passed_match:
                    stats["passed"] = int(passed_match.group(1))
                if failed_match:
                    stats["failed"] = int(failed_match.group(1))
                if xfailed_match:
                    stats["xfailed"] = int(xfailed_match.group(1))
                if skipped_match:
                    stats["skipped"] = int(skipped_match.group(1))
                break

        success = result.returncode == 0
        output = result.stdout + result.stderr if verbose else result.stderr

        return success, output, stats

    except subprocess.TimeoutExpired:
        return (
            False,
            "Timeout after 5 minutes",
            {"passed": 0, "failed": 0, "xfailed": 0, "skipped": 0},
        )
    except Exception as e:
        return (
            False,
            f"Error running tests: {e}",
            {"passed": 0, "failed": 0, "xfailed": 0, "skipped": 0},
        )


def main():
    """Main function to run all lab tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Run validation tests for all labs")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show verbose output for each lab"
    )
    parser.add_argument(
        "--fail-fast", action="store_true", help="Stop on first lab failure"
    )
    parser.add_argument("--lab-filter", help="Only run labs containing this substring")

    args = parser.parse_args()

    # Discover all labs
    all_labs = discover_labs()

    if args.lab_filter:
        all_labs = [lab for lab in all_labs if args.lab_filter in lab]

    if not all_labs:
        print("No labs found!")
        sys.exit(1)

    print(f"Found {len(all_labs)} labs to test")
    print("=" * 60)

    # Track results
    results = {}
    total_stats = {"passed": 0, "failed": 0, "xfailed": 0, "skipped": 0}

    start_time = time.time()

    # Run tests for each lab
    for i, lab in enumerate(all_labs, 1):
        print(f"[{i:3d}/{len(all_labs)}] Testing {lab}...", end=" ", flush=True)

        lab_start = time.time()
        success, output, stats = run_lab_tests(lab, args.verbose)
        lab_duration = time.time() - lab_start

        results[lab] = (success, output, stats, lab_duration)

        # Update totals
        for key in total_stats:
            total_stats[key] += stats[key]

        # Print result
        if success:
            test_summary = f"({stats['passed']} passed"
            if stats["xfailed"] > 0:
                test_summary += f", {stats['xfailed']} xfailed"
            if stats["skipped"] > 0:
                test_summary += f", {stats['skipped']} skipped"
            test_summary += f") [{lab_duration:.1f}s]"
            print(f"✓ {test_summary}")
        else:
            print(f"✗ FAILED [{lab_duration:.1f}s]")
            if args.verbose:
                print(f"  Error: {output}")

        if not success and args.fail_fast:
            print(f"\nStopping due to --fail-fast (failed on {lab})")
            break

    total_duration = time.time() - start_time

    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    successful_labs = sum(1 for success, _, _, _ in results.values() if success)
    failed_labs = len(results) - successful_labs

    print(
        f"Labs: {successful_labs} passed, {failed_labs} failed out of {len(results)} total"
    )
    print(
        f"Tests: {total_stats['passed']} passed, {total_stats['failed']} failed, "
        f"{total_stats['xfailed']} expected failures, {total_stats['skipped']} skipped"
    )
    print(f"Total time: {total_duration:.1f}s")

    if failed_labs > 0:
        print(f"\nFAILED LABS ({failed_labs}):")
        for lab, (success, output, _, duration) in results.items():
            if not success:
                print(f"  {lab} [{duration:.1f}s]")
                if not args.verbose and output.strip():
                    # Show first few lines of error
                    error_lines = output.strip().split("\n")[:3]
                    for line in error_lines:
                        print(f"    {line}")

    # Exit with error code if any lab failed
    sys.exit(failed_labs)


if __name__ == "__main__":
    main()
