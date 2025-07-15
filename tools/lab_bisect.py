#!/usr/bin/env python3
"""
Lab Bisection Tool for Batfish

This tool helps bisect lab failures by testing labs against different versions
of Batfish to find when a lab started failing.

Usage:
    python tools/lab_bisect.py --lab junos_as_path_acl --good-date 2022-09-01 --bad-date HEAD
"""

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class BatfishBisector:
    def __init__(self, batfish_dir: str, lab_name: str, verbose: bool = False):
        self.batfish_dir = Path(batfish_dir).resolve()
        self.lab_name = lab_name
        self.verbose = verbose
        self.server_process = None

        # Setup bisection log file
        self.log_file = Path(
            f"bisect_{lab_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        self.bisect_log = {
            "lab_name": lab_name,
            "start_time": datetime.now().isoformat(),
            "commits_tested": [],
        }

        # Setup logging
        level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=level, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Validate paths
        if not self.batfish_dir.exists():
            raise ValueError(f"Batfish directory not found: {self.batfish_dir}")

        self.bazel_run_script = self.batfish_dir / "tools" / "bazel_run.sh"
        if not self.bazel_run_script.exists():
            raise ValueError(f"bazel_run.sh not found: {self.bazel_run_script}")

    def log_commit_test(
        self,
        commit: str,
        result: Optional[bool],
        test_output: str = "",
        error_msg: str = "",
    ):
        """Log the result of testing a commit."""
        commit_info = {
            "commit": commit,
            "timestamp": datetime.now().isoformat(),
            "result": "GOOD"
            if result is True
            else "BAD"
            if result is False
            else "ERROR",
            "test_output": test_output,
            "error_msg": error_msg,
        }
        self.bisect_log["commits_tested"].append(commit_info)

        # Write to disk immediately for progress tracking
        with open(self.log_file, "w") as f:
            json.dump(self.bisect_log, f, indent=2)

        self.logger.info(
            f"Logged commit {commit[:8]} as {commit_info['result']} to {self.log_file}"
        )

    def finalize_log(self, first_bad_commit: Optional[str] = None):
        """Finalize the bisection log."""
        self.bisect_log["end_time"] = datetime.now().isoformat()
        self.bisect_log["first_bad_commit"] = first_bad_commit
        self.bisect_log["total_commits_tested"] = len(self.bisect_log["commits_tested"])

        with open(self.log_file, "w") as f:
            json.dump(self.bisect_log, f, indent=2)

        self.logger.info(f"Bisection complete. Full log saved to {self.log_file}")
        return self.log_file

    def _is_connection_error(self, test_output: str) -> bool:
        """Check if test output indicates a connection error to Batfish server."""
        connection_error_indicators = [
            "Connection refused",
            "ConnectionRefusedError",
            "Failed to establish a new connection",
            "NewConnectionError",
            "Max retries exceeded",
            "HTTPConnectionPool(host='localhost', port=9996)",
        ]
        return any(
            indicator in test_output for indicator in connection_error_indicators
        )

    def cleanup_containers(self) -> bool:
        """Remove containers directory to clear cached files."""
        try:
            containers_dir = self.batfish_dir / "containers"
            if containers_dir.exists():
                self.logger.info("Removing containers directory...")
                subprocess.run(["rm", "-rf", str(containers_dir)], check=True)
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to remove containers: {e}")
            return False

    def wait_for_server(self, timeout: int = 300) -> bool:
        """Wait for Batfish server to be ready on port 9996."""
        self.logger.info("Waiting for Batfish server to respond...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if process crashed
            if self.server_process and self.server_process.poll() is not None:
                self.logger.error("Batfish server process terminated")
                return False

            # Try to connect to the server
            try:
                with socket.create_connection(("localhost", 9996), timeout=2):
                    self.logger.info("Batfish server is ready!")
                    return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                # Server not ready yet, wait a bit
                time.sleep(5)

        self.logger.error(f"Batfish server did not respond within {timeout} seconds")
        return False

    def start_batfish_server(self) -> bool:
        """Start the Batfish server in the background."""
        try:
            self.logger.info("Starting Batfish server build and startup...")

            # Change to batfish directory and run the server
            env = os.environ.copy()
            self.server_process = subprocess.Popen(
                [str(self.bazel_run_script)],
                cwd=str(self.batfish_dir),
                stdout=subprocess.PIPE if not self.verbose else None,
                stderr=subprocess.PIPE if not self.verbose else None,
                env=env,
                preexec_fn=os.setsid,  # Create new process group
            )

            # Wait for server to actually be ready (not just built)
            return self.wait_for_server(
                timeout=600
            )  # 10 minute timeout for build + startup

        except Exception as e:
            self.logger.error(f"Failed to start Batfish server: {e}")
            return False

    def stop_batfish_server(self):
        """Stop the Batfish server."""
        if self.server_process:
            try:
                self.logger.info("Stopping Batfish server...")
                # Kill the process group to ensure all child processes are terminated
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)

                # Wait for graceful shutdown
                try:
                    self.server_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                    self.server_process.wait()

            except (ProcessLookupError, OSError):
                # Process already terminated
                pass
            finally:
                self.server_process = None

    def test_lab(self) -> tuple:
        """Test the specified lab and return (success, output)."""
        try:
            self.logger.info(f"Testing lab: {self.lab_name}")

            # Run pytest for the specific lab
            cmd = [
                "pytest",
                "lab_tests/test_labs.py",
                f"--labname={self.lab_name}",
                "-v",
                "--tb=short",  # Include short traceback for failures
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=300  # 5 minute timeout
            )

            output = f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

            if self.verbose:
                self.logger.debug(f"Test stdout: {result.stdout}")
                self.logger.debug(f"Test stderr: {result.stderr}")

            # Check for test success
            success = result.returncode == 0
            self.logger.info(f"Lab test {'PASSED' if success else 'FAILED'}")

            return success, output

        except subprocess.TimeoutExpired:
            self.logger.error("Lab test timed out")
            return False, "Test timed out after 300 seconds"
        except Exception as e:
            self.logger.error(f"Error running lab test: {e}")
            return False, f"Error running test: {e}"

    def git_checkout(self, commit: str) -> bool:
        """Checkout a specific commit in the batfish repository."""
        try:
            self.logger.info(f"Checking out commit: {commit}")

            result = subprocess.run(
                ["git", "checkout", commit],
                cwd=str(self.batfish_dir),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to checkout {commit}: {result.stderr}")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error checking out commit {commit}: {e}")
            return False

    def get_commit_from_date(self, date: str) -> Optional[str]:
        """Get the commit hash closest to a given date."""
        try:
            # Get commit hash from date
            result = subprocess.run(
                ["git", "rev-list", "-n", "1", f"--before={date}", "HEAD"],
                cwd=str(self.batfish_dir),
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                self.logger.error(f"Failed to get commit for date {date}")
                return None

            commit = result.stdout.strip()
            if not commit:
                self.logger.error(f"No commit found for date {date}")
                return None

            return commit

        except Exception as e:
            self.logger.error(f"Error getting commit for date {date}: {e}")
            return None

    def test_commit(self, commit: str, retry_count: int = 0) -> Optional[bool]:
        """Test a specific commit. Returns True if good, False if bad, None if error."""
        self.logger.info(f"Testing commit: {commit} (attempt {retry_count + 1})")
        error_msg = ""
        test_output = ""

        try:
            # Stop any running server
            self.stop_batfish_server()

            # Checkout the commit
            if not self.git_checkout(commit):
                error_msg = "Failed to checkout commit"
                self.log_commit_test(commit, None, test_output, error_msg)
                return None

            # Clean containers
            if not self.cleanup_containers():
                error_msg = "Failed to clean containers"
                self.log_commit_test(commit, None, test_output, error_msg)
                return None

            # Start server
            if not self.start_batfish_server():
                error_msg = "Failed to start Batfish server"
                # Retry once for server startup failures
                if retry_count == 0:
                    self.logger.warning(
                        f"Batfish server failed to start, retrying once..."
                    )
                    return self.test_commit(commit, retry_count + 1)
                else:
                    self.log_commit_test(commit, None, test_output, error_msg)
                    return None

            # Test the lab
            result, test_output = self.test_lab()

            # Check if the test failed due to connection errors (indicating server issues)
            if not result and self._is_connection_error(test_output):
                # Stop server and retry once for connection errors
                self.stop_batfish_server()
                if retry_count == 0:
                    self.logger.warning(f"Connection error detected, retrying once...")
                    return self.test_commit(commit, retry_count + 1)
                else:
                    # After retry, treat as skip (return None) rather than failure (return False)
                    error_msg = "Connection error persisted after retry - skipping"
                    self.log_commit_test(commit, None, test_output, error_msg)
                    return None

            # Stop server
            self.stop_batfish_server()

            # Log the test result
            self.log_commit_test(commit, result, test_output, error_msg)

            return result

        except Exception as e:
            error_msg = f"Exception during test: {e}"
            self.log_commit_test(commit, None, test_output, error_msg)
            self.stop_batfish_server()  # Ensure cleanup
            return None

    def bisect(
        self, good_commit: str, bad_commit: str, skip_validation: bool = False
    ) -> Optional[str]:
        """
        Perform bisection to find the first bad commit.
        Returns the first bad commit hash, or None if bisection fails.
        """
        self.logger.info(f"Starting bisection between {good_commit} and {bad_commit}")

        # Reset to origin/master first to ensure clean state
        self.logger.info("Resetting batfish repository to origin/master...")
        try:
            subprocess.run(
                ["git", "checkout", "origin/master"],
                cwd=str(self.batfish_dir),
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to reset to origin/master: {e}")
            return None

        # Validate the bisection range first (unless skipped)
        if not skip_validation:
            self.logger.info("Validating bisection range...")

            # Test the good commit - should pass
            self.logger.info("Testing supposed 'good' commit...")
            good_result = self.test_commit(good_commit)
            if good_result is None:
                self.logger.error(
                    "Could not test the 'good' commit - skipping bisection"
                )
                return None
            elif not good_result:
                self.logger.error(
                    f"The 'good' commit {good_commit} is actually BAD! Cannot bisect."
                )
                self.logger.error("Try an earlier commit as the good starting point.")
                return None
            else:
                self.logger.info(f"✓ Good commit {good_commit} passes as expected")

            # Test the bad commit - should fail
            self.logger.info("Testing supposed 'bad' commit...")
            bad_result = self.test_commit(bad_commit)
            if bad_result is None:
                self.logger.error(
                    "Could not test the 'bad' commit - skipping bisection"
                )
                return None
            elif bad_result:
                self.logger.warning(f"The 'bad' commit {bad_commit} is actually GOOD!")
                self.logger.warning(
                    "This means the issue has been fixed or never existed."
                )
                self.logger.warning(
                    "No bisection needed - the lab is currently passing."
                )
                return None
            else:
                self.logger.info(f"✓ Bad commit {bad_commit} fails as expected")

            self.logger.info("Range validation complete - proceeding with bisection")
        else:
            self.logger.info(
                "Skipping range validation - proceeding directly to bisection"
            )

        try:
            # Start git bisect
            subprocess.run(
                ["git", "bisect", "reset"],
                cwd=str(self.batfish_dir),
                capture_output=True,
            )

            subprocess.run(
                ["git", "bisect", "start"],
                cwd=str(self.batfish_dir),
                check=True,
                capture_output=True,
            )

            subprocess.run(
                ["git", "bisect", "bad", bad_commit],
                cwd=str(self.batfish_dir),
                check=True,
                capture_output=True,
            )

            subprocess.run(
                ["git", "bisect", "good", good_commit],
                cwd=str(self.batfish_dir),
                check=True,
                capture_output=True,
            )

            while True:
                # Get current commit
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=str(self.batfish_dir),
                    capture_output=True,
                    text=True,
                    check=True,
                )
                current_commit = result.stdout.strip()

                # Test current commit
                test_result = self.test_commit(current_commit)

                if test_result is None:
                    self.logger.error("Failed to test commit, skipping...")
                    subprocess.run(
                        ["git", "bisect", "skip"],
                        cwd=str(self.batfish_dir),
                        check=True,
                        capture_output=True,
                    )
                    continue

                # Mark as good or bad
                mark = "good" if test_result else "bad"
                result = subprocess.run(
                    ["git", "bisect", mark],
                    cwd=str(self.batfish_dir),
                    capture_output=True,
                    text=True,
                )

                # Check if bisection is complete
                if "is the first bad commit" in result.stdout:
                    # Extract the bad commit hash
                    lines = result.stdout.split("\n")
                    for line in lines:
                        if "is the first bad commit" in line:
                            bad_commit_hash = line.split()[0]
                            self.logger.info(
                                f"Found first bad commit: {bad_commit_hash}"
                            )
                            self.finalize_log(bad_commit_hash)
                            return bad_commit_hash
                elif result.returncode == 0:
                    # Continue bisection
                    continue
                else:
                    self.logger.error("Bisection completed without finding bad commit")
                    break

        except Exception as e:
            self.logger.error(f"Error during bisection: {e}")
        finally:
            # Clean up bisection
            try:
                subprocess.run(
                    ["git", "bisect", "reset"],
                    cwd=str(self.batfish_dir),
                    capture_output=True,
                )
            except:
                pass

        self.finalize_log(None)
        return None


def main():
    parser = argparse.ArgumentParser(description="Bisect lab failures in Batfish")
    parser.add_argument("--lab", required=True, help="Lab name to test")
    parser.add_argument(
        "--batfish-dir",
        default="../batfish",
        help="Path to batfish repository (default: ../batfish)",
    )
    parser.add_argument(
        "--good-date", help="Date when lab was known to pass (YYYY-MM-DD)"
    )
    parser.add_argument("--good-commit", help="Commit hash when lab was known to pass")
    parser.add_argument(
        "--bad-date", help="Date when lab was known to fail (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--bad-commit",
        default="HEAD",
        help="Commit hash when lab was known to fail (default: HEAD)",
    )
    parser.add_argument("--test-only", help="Test a specific commit without bisecting")
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip validation of good/bad commits before bisecting",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    try:
        bisector = BatfishBisector(args.batfish_dir, args.lab, args.verbose)

        if args.test_only:
            # Just test a specific commit
            result = bisector.test_commit(args.test_only)
            log_file = bisector.finalize_log(None)
            print(f"Test log saved to: {log_file}")

            if result is None:
                print(f"Failed to test commit {args.test_only}")
                sys.exit(1)
            elif result:
                print(f"Commit {args.test_only}: GOOD")
                sys.exit(0)
            else:
                print(f"Commit {args.test_only}: BAD")
                sys.exit(1)

        # Determine good and bad commits
        if args.good_commit:
            good_commit = args.good_commit
        elif args.good_date:
            good_commit = bisector.get_commit_from_date(args.good_date)
            if not good_commit:
                print(f"Could not find commit for good date: {args.good_date}")
                sys.exit(1)
        else:
            print("Must specify either --good-date or --good-commit")
            sys.exit(1)

        if args.bad_commit != "HEAD":
            bad_commit = args.bad_commit
        elif args.bad_date:
            bad_commit = bisector.get_commit_from_date(args.bad_date)
            if not bad_commit:
                print(f"Could not find commit for bad date: {args.bad_date}")
                sys.exit(1)
        else:
            bad_commit = "HEAD"

        print(
            f"Bisecting between good commit: {good_commit} and bad commit: {bad_commit}"
        )

        # Perform bisection
        first_bad = bisector.bisect(good_commit, bad_commit, args.skip_validation)

        if first_bad:
            print(f"\nFirst bad commit found: {first_bad}")

            # Show commit details
            result = subprocess.run(
                ["git", "show", "--stat", first_bad],
                cwd=str(bisector.batfish_dir),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print("\nCommit details:")
                print(result.stdout)
        else:
            print("Could not find the first bad commit")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nBisection interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
