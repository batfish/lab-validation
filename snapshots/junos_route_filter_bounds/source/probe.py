"""Commit and evaluate each route-filter case on the lab's Junos node."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from lab_builder.containerlab import inspect
from lab_builder.device import connect

SOURCE = Path(__file__).resolve().parent
CLI_ERROR = re.compile(r"error:|syntax error|^\s*\^\s*$", re.I | re.M)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--case", action="append", help="Run selected named cases")
    args = parser.parse_args()
    cases = json.loads((SOURCE / "cases.json").read_text())
    if args.case:
        selected = set(args.case)
        cases = [case for case in cases if case["name"] in selected]
        assert {case["name"] for case in cases} == selected, args.case
    args.output_dir.mkdir(parents=True, exist_ok=True)
    nodes = inspect(SOURCE / "topology.clab.yml")
    assert len(nodes) == 1
    conn = connect(nodes[0])
    results = []
    try:
        version = conn.send_command("show version", read_timeout=30)
        (args.output_dir / "version.txt").write_text(version + "\n")
        candidates = json.loads((SOURCE / "candidates.json").read_text())
        for family, table in [("4", "inet.0"), ("6", "inet6.0")]:
            routes = conn.send_command(
                f"show route table {table} terse", read_timeout=30
            )
            (args.output_dir / f"routes-v{family}.txt").write_text(routes + "\n")
            for prefix in candidates[family]:
                assert prefix in routes, f"Candidate route is absent: {prefix}"
        conn.config_mode()
        for case in cases:
            name = case["name"]
            policy = f"RF-{name}"
            transcript = []

            def command(text: str) -> str:
                output = conn.send_command(text, expect_string=r"#", read_timeout=30)
                transcript.append(f"{text}\n{output}")
                return output

            command("rollback 0")
            command(f"delete policy-options policy-statement {policy}")
            lines = [
                f"set policy-options policy-statement {policy} term MATCH "
                f"from route-filter {route_filter}"
                for route_filter in case["filters"]
            ]
            lines += [
                f"set policy-options policy-statement {policy} term MATCH then accept",
                f"set policy-options policy-statement {policy} term REJECT then reject",
            ]
            cli_accepted = True
            for line in lines:
                if CLI_ERROR.search(command(line)):
                    cli_accepted = False
                    break
            result = {
                "name": name,
                "filters": case["filters"],
                "cli_accepted": cli_accepted,
                "commit_check": None,
                "committed": False,
            }
            if cli_accepted:
                check = command("commit check")
                assert (
                    "configuration check succeeds" in check or "error:" in check.lower()
                ), f"Indeterminate commit check: {check}"
                result["commit_check"] = "configuration check succeeds" in check
                if result["commit_check"]:
                    commit = command("commit")
                    assert "commit complete" in commit, commit
                    result["committed"] = True
            if not result["committed"]:
                command("rollback 0")
            if result["committed"]:
                # test policy reads the real RIB. The startup config installs
                # every candidate as an active static discard route.
                family = "::/0" if case["family"] == 6 else "0.0.0.0/0"
                output = command(f"run test policy {policy} {family}")
                assert "syntax error" not in output.lower(), output
                result["policy_output"] = output
            result["warnings"] = [
                line
                for text in transcript
                if text.startswith(("set ", "commit"))
                for line in text.splitlines()
                if "warning:" in line.lower()
            ]
            (args.output_dir / f"{name}.txt").write_text("\n\n".join(transcript) + "\n")
            results.append(result)
            (args.output_dir / "results.json").write_text(
                json.dumps(results, indent=2) + "\n"
            )
            print(
                f"{name}: cli={cli_accepted}, commit_check={result['commit_check']}, "
                f"committed={result['committed']}, warnings={len(result['warnings'])}",
                flush=True,
            )
    finally:
        if conn.check_config_mode():
            conn.send_command("rollback 0", expect_string=r"#", read_timeout=30)
            conn.exit_config_mode()
        conn.disconnect()


if __name__ == "__main__":
    main()
