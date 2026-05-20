#!/usr/bin/env python3
"""Per-term commit-check iterator for junos-then-action-conflicts.

Runs on the EC2 host. For each of the 112 dut terms (and 112 sender
TAG-N terms, plus per-prefix static routes), pushes the term's set-
form lines, runs `commit check`, and records:

  * "accepts"   -> term commits cleanly (default expectation).
  * "rejects"   -> Junos rejects with a definitive error.
  * "indeterminate" -> exception/timeout/empty output.

After commit check, ALWAYS rolls back so the device stays clean
between probes. After all dut terms have been classified, this script
emits a `commit-results.yaml` summarizing per-term outcomes.

The expected workflow on EC2 is:

  1. Deploy minimal lab (boots in ~3 min).
  2. Run:  python3 push-terms.py probe-dut
       -> writes commit-results.yaml
  3. Run:  python3 push-terms.py apply-dut
       -> pushes only the accepts to dut and commits.
  4. Run:  python3 push-terms.py apply-sender
       -> pushes the 112 sender terms (all should accept since they
          only reference the marker community, which is benign).
  5. Validate, collect, build snapshot.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).parent
TERM_METADATA = HERE / "term-metadata.yaml"
RESULTS_FILE = HERE / "commit-results.yaml"

# Set in main() after parsing args.
LAB_DIR_ON_EC2: Path | None = None


# ---------------------------------------------------------------------------
# netmiko interaction with Junos
# ---------------------------------------------------------------------------


def _connect(host: str, password: str = "admin@123"):
    from netmiko import ConnectHandler

    return ConnectHandler(
        device_type="juniper_junos",
        host=host,
        username="admin",
        password=password,
        timeout=30,
        session_timeout=120,
        ssh_strict=False,
        system_host_keys=False,
        alt_host_keys=False,
    )


def commit_check_one(conn, set_lines: list[str]) -> tuple[str, str]:
    """Push set_lines on existing conn, run `commit check`, rollback.

    Conn must already be in config_mode. Stays in config_mode on return.
    """
    try:
        for line in set_lines:
            line = line.strip()
            if not line:
                continue
            conn.send_command_timing(line)
        output = conn.send_command("commit check", expect_string=r"#", read_timeout=30)
        conn.send_command_timing("rollback 0")
    except Exception as e:
        try:
            conn.send_command_timing("rollback 0")
        except Exception:
            pass
        return "indeterminate", f"exception: {e}"

    text = output.strip()
    lower = text.lower()
    if "configuration check succeeds" in lower:
        return "accepts", text
    if "error" in lower or "syntax error" in lower or "failed" in lower:
        return "rejects", text
    if not text:
        return "indeterminate", "empty output"
    return "indeterminate", text


def push_and_commit(host: str, set_lines: list[str]) -> str:
    """Push set_lines via load-set-terminal and commit."""
    conn = _connect(host)
    try:
        conn.config_mode()
        blob = "\n".join(line.strip() for line in set_lines if line.strip())
        conn.send_command_timing("load set terminal", delay_factor=2)
        load_out = conn.send_command_timing(
            blob + "\n\x04",
            strip_prompt=False,
            strip_command=False,
            delay_factor=4,
        )
        commit_out = conn.send_command("commit", expect_string=r"#", read_timeout=300)
        conn.exit_config_mode()
        return load_out + "\n" + commit_out
    finally:
        conn.disconnect()


# ---------------------------------------------------------------------------
# Term -> set-line rendering
# ---------------------------------------------------------------------------


POLICY_PREFIX = "set policy-options policy-statement IMPORT term"


def dut_term_set_lines(term: dict) -> list[str]:
    """Render a term as set-format lines on dut.

    Layout:
      set policy-options policy-statement IMPORT term <NAME> from route-filter <PFX> exact
      set policy-options policy-statement IMPORT term <NAME> then <action_1>
      set policy-options policy-statement IMPORT term <NAME> then <action_2>
      ...
      [accept]   <- only if no terminator already present
      <reorder term before REJECT-OTHER>
    """
    name = term["name"]
    prefix = term["prefix"]
    actions = list(term["actions"])
    # Mirror the assembler's logic: append accept if no terminator.
    terminators = {"accept", "reject", "next term", "next policy"}
    has_terminator = any(a.strip() in terminators for a in actions)
    if not has_terminator:
        actions.append("accept")

    lines: list[str] = [
        f"{POLICY_PREFIX} {name} from route-filter {prefix} exact",
    ]
    for a in actions:
        lines.append(f"{POLICY_PREFIX} {name} then {a}")
    # Place this term before REJECT-OTHER (Junos order matters in policy).
    lines.append(
        f"insert policy-options policy-statement IMPORT term {name} before term REJECT-OTHER"
    )
    return lines


def sender_term_set_lines(term: dict) -> list[str]:
    """Sender adds a static route + a TAG-N export term.

    The TAG-N term tags the matching prefix with the per-term marker community
    65001:<term-id> plus any input_communities.
    """
    tid = term["term_id"]
    prefix = term["prefix"]
    payload = term.get("input_communities") or []

    lines: list[str] = [
        # Per-term marker community definition.
        f"set policy-options community MARK-{tid} members 65001:{tid}",
        # Static route for sender to originate.
        f"set routing-options static route {prefix} discard",
    ]
    base = f"set policy-options policy-statement EXPORT-TO-DUT term TAG-{tid}"
    lines.append(f"{base} from protocol static")
    lines.append(f"{base} from route-filter {prefix} exact")
    lines.append(f"{base} then community add MARK-{tid}")
    for c in payload:
        lines.append(f"{base} then community add {c}")
    lines.append(f"{base} then accept")
    lines.append(
        "insert policy-options policy-statement EXPORT-TO-DUT "
        f"term TAG-{tid} before term REJECT-OTHER"
    )
    return lines


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------


def get_node_ip(node_name: str) -> str:
    """Return the management IP of a containerlab node by name."""
    sys.path.insert(0, "/home/ubuntu/lab/src")
    from lab_builder import containerlab as clab

    nodes = clab.inspect(str(LAB_DIR_ON_EC2 / "topology.clab.yml"))
    for n in nodes:
        if n.name == node_name:
            return n.management_ip
    raise RuntimeError(f"could not find {node_name} in {[n.name for n in nodes]}")


def _bulk_commit_check(
    conn, all_lines: list[str], term_index: dict[int, dict]
) -> tuple[str, set[int]]:
    """Push all_lines, run `commit check`, rollback. Return (output, rejected_term_ids).

    Junos commit-check error messages identify the offending hierarchy
    line. If the failed lines reference a `term <NAME>` we can map back
    to term_index by name. Bulk-push is fast (~30s for ~600 lines)
    versus per-term (~10s × 112 = 18 min).
    """
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
        conn.send_command_timing(line)
    output = conn.send_command("commit check", expect_string=r"#", read_timeout=120)
    conn.send_command_timing("rollback 0")
    return output, set()


def _push_then_diff(
    conn, all_lines: list[str], expected_terms: list[dict]
) -> tuple[str, set[str]]:
    """Push all_lines, commit-check, examine candidate config to see which
    expected terms actually made it in.

    Returns (commit_check_output, set_of_terms_present_in_candidate_config).
    Always rolls back at the end.
    """
    for line in all_lines:
        line = line.strip()
        if not line:
            continue
        conn.send_command_timing(line)

    # Snapshot candidate config (everything we just pushed plus existing).
    show_out = conn.send_command(
        "show policy-options policy-statement IMPORT | display set",
        expect_string=r"#",
        read_timeout=60,
    )
    cc_out = conn.send_command("commit check", expect_string=r"#", read_timeout=120)
    conn.send_command_timing("rollback 0")

    present = set()
    for t in expected_terms:
        if re.search(rf"\bterm {re.escape(t['name'])}\b", show_out):
            present.add(t["name"])
    return cc_out, present


def probe_dut() -> None:
    """Bulk-push every term to dut. Binary-search any rejection.

    Strategy:
      1. Push all 112 terms' set lines in one shot.
      2. Run `commit check`. If it succeeds, all 112 accept.
      3. If it fails, binary-search: split candidate set in half, push
         each half from a clean state, repeat until each rejected term
         is isolated. Bulk-success on the surviving subset becomes the
         final accepts list.
    """
    terms = yaml.safe_load(TERM_METADATA.read_text())["terms"]
    host = get_node_ip("dut")
    print(f"Probing {len(terms)} terms against dut at {host}", flush=True)

    conn = _connect(host)
    conn.config_mode()
    try:
        accepts: list[dict] = []
        rejects: list[dict] = []
        indeterminate: list[dict] = []
        bisect_subset(conn, terms, accepts, rejects, indeterminate, depth=0)
    finally:
        try:
            conn.exit_config_mode()
        except Exception:
            pass
        conn.disconnect()

    results = []
    for t in accepts:
        results.append({**_term_summary(t), "outcome": "accepts"})
    for t in rejects:
        results.append(
            {
                **_term_summary(t),
                "outcome": "rejects",
                "rejection_output": t.get("_rejection_output", ""),
            }
        )
    for t in indeterminate:
        results.append({**_term_summary(t), "outcome": "indeterminate"})
    results.sort(key=lambda r: r["term_id"])
    RESULTS_FILE.write_text(yaml.safe_dump({"results": results}, sort_keys=False))
    print(
        f"\nSummary: accepts={len(accepts)} rejects={len(rejects)} "
        f"indeterminate={len(indeterminate)}"
    )
    print(f"Wrote {RESULTS_FILE}")


def _term_summary(t: dict) -> dict:
    return {
        "term_id": t["term_id"],
        "name": t["name"],
        "section": t["section"],
        "prefix": t["prefix"],
        "set_lines": dut_term_set_lines(t),
    }


def _push_lines_bulk(conn, all_lines: list[str], host: str | None = None) -> str:
    """Push set-format lines via `load set terminal` (single command, fast).

    Junos's `load set terminal` reads pasted set-form lines until ^D.
    All lines must be plain ASCII without `[`/`]` (CLI multi-value
    syntax) since that confuses interactive paste; manifests have
    been desugared to plain `community set X` lines.
    """
    blob = "\n".join(line.strip() for line in all_lines if line.strip())
    out1 = conn.send_command_timing("load set terminal")
    out2 = conn.send_command_timing(
        blob + "\n\x04", strip_prompt=False, strip_command=False
    )
    return out1 + out2


def bisect_subset(
    conn,
    subset: list[dict],
    accepts: list[dict],
    rejects: list[dict],
    indeterminate: list[dict],
    depth: int,
) -> None:
    """Try to commit `subset` as a unit. If accept, mark all accepts.
    If reject, split and recurse. If indeterminate, mark all indeterminate.
    """
    indent = "  " * depth
    if not subset:
        return
    print(
        f"{indent}probe |{len(subset):3d}| terms ({subset[0]['term_id']}..{subset[-1]['term_id']})",
        flush=True,
    )
    all_lines: list[str] = []
    for t in subset:
        all_lines.extend(dut_term_set_lines(t))
    output = ""
    try:
        load_out = _push_lines_bulk(conn, all_lines)
        output = conn.send_command("commit check", expect_string=r"#", read_timeout=120)
        # Surface load-time errors too.
        if "syntax error" in load_out.lower() or "error: " in load_out.lower():
            output = load_out + "\n" + output
    except Exception as e:
        output = f"exception: {e}"
    finally:
        try:
            conn.send_command_timing("rollback 0")
        except Exception:
            pass

    text = output.strip()
    lower = text.lower()
    if "configuration check succeeds" in lower:
        print(f"{indent}  ACCEPT all {len(subset)}", flush=True)
        accepts.extend(subset)
        return
    if "error" in lower or "syntax error" in lower or "failed" in lower:
        if len(subset) == 1:
            t = subset[0]
            t["_rejection_output"] = text
            print(f"{indent}  REJECT term {t['term_id']} {t['name']}", flush=True)
            print(f"{indent}    {text[:200]}", flush=True)
            rejects.append(t)
            return
        mid = len(subset) // 2
        bisect_subset(conn, subset[:mid], accepts, rejects, indeterminate, depth + 1)
        bisect_subset(conn, subset[mid:], accepts, rejects, indeterminate, depth + 1)
        return
    if not text:
        print(
            f"{indent}  INDETERMINATE (empty output) for {len(subset)} terms",
            flush=True,
        )
        indeterminate.extend(subset)
        return
    if len(subset) == 1:
        t = subset[0]
        t["_rejection_output"] = text
        print(f"{indent}  INDETERMINATE term {t['term_id']}", flush=True)
        indeterminate.append(t)
        return
    mid = len(subset) // 2
    bisect_subset(conn, subset[:mid], accepts, rejects, indeterminate, depth + 1)
    bisect_subset(conn, subset[mid:], accepts, rejects, indeterminate, depth + 1)


def reset_dut() -> None:
    """Delete every IMPORT term except REJECT-OTHER from dut."""
    terms = yaml.safe_load(TERM_METADATA.read_text())["terms"]
    host = get_node_ip("dut")
    delete_lines = [
        f"delete policy-options policy-statement IMPORT term {t['name']}" for t in terms
    ]
    print(f"Resetting {len(delete_lines)} terms on dut at {host}", flush=True)
    output = push_and_commit(host, delete_lines)
    print(output[-2000:])


def apply_dut() -> None:
    """Push all `accepts` terms to dut and commit."""
    if not RESULTS_FILE.exists():
        print(f"Run probe-dut first to produce {RESULTS_FILE}")
        sys.exit(1)
    data = yaml.safe_load(RESULTS_FILE.read_text())
    accepted = [r for r in data["results"] if r["outcome"] == "accepts"]
    host = get_node_ip("dut")
    print(f"Applying {len(accepted)} accepted terms to dut at {host}")
    all_lines: list[str] = []
    for r in accepted:
        all_lines.extend(r["set_lines"])
    output = push_and_commit(host, all_lines)
    print(output[-2000:])


def apply_sender() -> None:
    """Push all sender TAG-N terms and static routes."""
    terms = yaml.safe_load(TERM_METADATA.read_text())["terms"]
    host = get_node_ip("sender")
    print(f"Pushing {len(terms)} sender terms to {host}")
    all_lines: list[str] = []
    for t in terms:
        all_lines.extend(sender_term_set_lines(t))
    output = push_and_commit(host, all_lines)
    print(output[-2000:])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lab-dir",
        default="/home/ubuntu/lab/junos-then-action-conflicts",
        help="EC2 path to lab dir (containing topology.clab.yml)",
    )
    parser.add_argument(
        "command",
        choices=["probe-dut", "apply-dut", "apply-sender", "reset-dut"],
    )
    args = parser.parse_args()

    global LAB_DIR_ON_EC2
    LAB_DIR_ON_EC2 = Path(args.lab_dir)

    if args.command == "probe-dut":
        probe_dut()
    elif args.command == "apply-dut":
        apply_dut()
    elif args.command == "apply-sender":
        apply_sender()
    elif args.command == "reset-dut":
        reset_dut()


if __name__ == "__main__":
    main()
