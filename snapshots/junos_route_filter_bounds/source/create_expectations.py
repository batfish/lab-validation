"""Derive policy expectations and result tables from the captured Junos run."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
from pathlib import Path

import yaml

SOURCE = Path(__file__).resolve().parent
PREFIX_LINE = re.compile(r"(?m)^([0-9a-fA-F:.]+/\d+)(?:\s|$)")


def accepted_prefixes(output: str) -> set[str]:
    assert re.search(r"Policy RF-\S+: \d+ prefix accepted, \d+ prefix rejected", output)
    return {
        str(ipaddress.ip_network(prefix, strict=False))
        for prefix in PREFIX_LINE.findall(output)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batfish-resources", type=Path)
    args = parser.parse_args()
    cases = json.loads((SOURCE / "cases.json").read_text())
    candidates = json.loads((SOURCE / "candidates.json").read_text())
    results = {
        result["name"]: result
        for result in json.loads(
            (SOURCE.parent / "show/dut/route_filter_tests/results.json").read_text()
        )
    }
    assert set(results) == {case["name"] for case in cases}
    policies = {}
    warnings = []
    host_nos = {"dut": "junos"}
    warning_spec = {
        "strict": True,
        "expects_fatal_warning": [],
        "expects_risky_warning": [],
    }
    all_config = ["set system host-name route-filter-bounds"]
    valid_config = ["set system host-name route-filter-bounds-valid"]
    matches = []
    table = [
        "# Junos 25.4R1.12 route-filter results",
        "",
        "Every route-filter statement was accepted by the CLI. The table records",
        "commit-check results; each passing check was followed by a commit.",
        "No case produced a warning during loading, checking, or committing.",
        "",
        "Matched prefixes are restricted to the candidates in `candidates.json`.",
        "The full device output is in `../show/dut/route_filter_tests/<case>.txt`.",
        "",
        "| Case | Route filters | Commits | Candidate matches |",
        "| --- | --- | --- | --- |",
    ]
    for case in cases:
        name = case["name"]
        result = results[name]
        assert result["filters"] == case["filters"]
        assert result["cli_accepted"]
        assert not result["warnings"]
        assert result["commit_check"] == result["committed"]
        policy = f"RF-{name}"
        lines = [
            f"set policy-options policy-statement {policy} term MATCH "
            f"from route-filter {route_filter}"
            for route_filter in case["filters"]
        ]
        lines += [
            f"set policy-options policy-statement {policy} term MATCH then accept",
            f"set policy-options policy-statement {policy} term REJECT then reject",
        ]
        all_config += lines
        accepted = (
            accepted_prefixes(result["policy_output"]) if result["committed"] else set()
        )
        candidate_matches = sorted(
            accepted.intersection(candidates[str(case["family"])])
        )
        severity = None
        if not result["committed"]:
            severity = "fatal"
            warnings.append(f"FATAL {policy}")
        elif not accepted or "-shadow-" in name:
            severity = "risky"
            warnings.append(f"RISK {policy}")
        host = f"case-{name}"
        host_nos[host] = "junos"
        fixture_dir = SOURCE.parent / "configs" / host
        fixture_dir.mkdir(exist_ok=True)
        (fixture_dir / "case.cfg").write_text(
            f"# Parser fixture for the recorded Junos case {name}.\n"
            f"set system host-name {host}\n" + "\n".join(lines) + "\n"
        )
        if severity:
            warning_spec[f"expects_{severity}_warning"].append(
                {"host": host, "contains": f"policy-statement {policy} term MATCH"}
            )
            if result["committed"]:
                warning_spec["expects_risky_warning"].append(
                    {"host": "dut", "contains": f"policy-statement {policy} term MATCH"}
                )
        if result["committed"] and case["family"] == 4:
            valid_config += lines
            policies[policy] = candidate_matches
            matches += [
                f"{policy} {prefix} {str(prefix in accepted).lower()}"
                for prefix in candidates["4"]
            ]
        filters = "<br>".join(f"`{value}`" for value in case["filters"])
        matched = ", ".join(f"`{value}`" for value in candidate_matches) or (
            "None" if result["committed"] else "Not committed"
        )
        table.append(
            f"| {name} | {filters} | {'Yes' if result['committed'] else 'No'} | {matched} |"
        )
    validation = SOURCE.parent / "validation"
    validation.mkdir(exist_ok=True)
    (validation / "routing_policy_matches.json").write_text(
        json.dumps(
            {"node": "dut", "routes": candidates["4"], "policies": policies}, indent=2
        )
        + "\n"
    )
    (validation / "parse_warnings.yaml").write_text(
        yaml.safe_dump(warning_spec, sort_keys=False)
    )
    (SOURCE.parent / "show/host_nos.txt").write_text(
        json.dumps(host_nos, indent=2) + "\n"
    )
    (validation / "sickbay.yaml").write_text(
        yaml.safe_dump(
            {
                "entries": [
                    {
                        "hostname": "case-.*",
                        "test_name": test,
                        "skip": {
                            "skip_type": "dont_run",
                            "reason": "Parser fixtures have no collected device state.",
                        },
                    }
                    for test in [
                        "test_interface_properties",
                        "test_main_rib_routes",
                        "test_bgp_rib_routes",
                        "test_evpn_rib_routes",
                    ]
                ]
            },
            sort_keys=False,
        )
    )
    (SOURCE / "results.md").write_text("\n".join(table) + "\n")
    if args.batfish_resources:
        for name, lines in [
            ("route-filter-bounds", all_config),
            ("route-filter-bounds-valid", valid_config),
            ("route-filter-bounds-warnings", warnings),
            ("route-filter-bounds-matches", matches),
        ]:
            (args.batfish_resources / name).write_text("\n".join(lines) + "\n")
    print(
        f"{len(cases)} cases, {len(policies)} IPv4 policies, {len(matches)} route checks"
    )


if __name__ == "__main__":
    main()
