#!/usr/bin/env python3
"""Assemble dut.cfg, sender.cfg, and a master term metadata YAML from
the per-section manifest YAMLs."""

from pathlib import Path

import yaml

HERE = Path(__file__).parent
LAB_DIR = HERE.parent  # snapshots/junos_then_action_conflicts/source/
CONFIGS_DIR = LAB_DIR / "configs"

MANIFESTS = [
    HERE / "manifest-1-scalars.yaml",
    HERE / "manifest-2-numeric.yaml",
    HERE / "manifest-3-aspath.yaml",
    HERE / "manifest-4-community.yaml",
    HERE / "manifest-5-flowcontrol.yaml",
]


def load_terms() -> tuple[list[dict], list[str]]:
    """Return (all_terms, all_stubs).

    Each term gets `section_label` derived from the manifest section field
    and a `community_input` list (default empty) for sender pre-tagging.
    """
    all_terms = []
    all_stubs: list[str] = []
    seen_term_ids: set[int] = set()
    seen_prefixes: set[str] = set()
    for path in MANIFESTS:
        with path.open() as fh:
            data = yaml.safe_load(fh)
        section = data["section"]
        for stub in data.get("stubs") or []:
            if stub not in all_stubs:
                all_stubs.append(stub)
        for term in data["terms"]:
            tid = term["term_id"]
            pfx = term["prefix"]
            if tid in seen_term_ids:
                raise ValueError(f"duplicate term_id {tid}")
            if pfx in seen_prefixes:
                raise ValueError(f"duplicate prefix {pfx} (term_id {tid})")
            seen_term_ids.add(tid)
            seen_prefixes.add(pfx)
            term["manifest_section"] = section
            term.setdefault("input_communities", [])
            # Section label for README grouping.
            sub = term.get("section") or section.split("-", 1)[0]
            term["section_label"] = str(sub)
            all_terms.append(term)
    return all_terms, all_stubs


def section_has_terminator(actions: list[str]) -> bool:
    """Return True if `actions` already contains a flow terminator."""
    terminators = {"accept", "reject", "next term", "next policy"}
    for a in actions:
        if a.strip() in terminators:
            return True
    return False


def render_term(term: dict, rejection: str | None = None) -> list[str]:
    """Return the lines of a `term NAME { ... }` block (4-space indented).

    Each term includes:
        from { route-filter <prefix> exact; }
        then { <actions>; [accept;] }

    A trailing `accept` is appended to actions UNLESS the actions already
    contain a terminator (§5/§6 cases).

    If `rejection` is provided, the term is wrapped in a /* COMMIT-REJECTED */
    block instead, with the original source preserved as a comment for
    documentation but ignored at commit time.
    """
    name = term["name"]
    prefix = term["prefix"]
    desc = term.get("description", "")
    actions = list(term["actions"])
    if not section_has_terminator(actions):
        actions.append("accept")

    lines = []
    if rejection:
        lines.append(f"        /* COMMIT-REJECTED: term {term['term_id']} {name}")
        lines.append(f"         * {rejection}")
        lines.append("         *")
        lines.append(
            "         * Original source preserved here for reference; do not uncomment."
        )
        lines.append("         *")
        lines.append(f"         * term {name} {{")
        lines.append("         *     from {")
        lines.append(f"         *         route-filter {prefix} exact;")
        lines.append("         *     }")
        lines.append("         *     then {")
        for a in actions:
            lines.append(f"         *         {a};")
        lines.append("         *     }")
        lines.append("         * }")
        lines.append("         */")
        return lines
    if desc:
        lines.append(f"        /* term {term['term_id']}: {desc} */")
    lines.append(f"        term {name} {{")
    lines.append("            from {")
    lines.append(f"                route-filter {prefix} exact;")
    lines.append("            }")
    lines.append("            then {")
    for a in actions:
        lines.append(f"                {a};")
    lines.append("            }")
    lines.append("        }")
    return lines


def load_rejections() -> dict[int, str]:
    """Map term_id -> first-line rejection reason from commit-results.yaml."""
    path = HERE / "commit-results.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text())
    out: dict[int, str] = {}
    for r in data.get("results", []):
        if r["outcome"] == "rejects":
            text = (r.get("rejection_output") or "").strip()
            # Take just the most informative line.
            for line in text.splitlines():
                line = line.strip()
                if line and not line.startswith("[") and "error:" not in line.lower():
                    out[r["term_id"]] = line
                    break
            else:
                out[r["term_id"]] = (
                    text.splitlines()[0] if text else "rejected at commit time"
                )
    return out


def render_dut_cfg(
    terms: list[dict], stubs: list[str], comment_rejections: bool = True
) -> str:
    """Build dut.cfg as a hierarchical Junos config.

    When comment_rejections is True (default), terms that Junos rejects at
    commit time are wrapped in /* COMMIT-REJECTED */ blocks (loadable form).
    When False, every term is rendered as live config — the
    "intended pre-collapse" view, useful as a visual reference for
    diffing against the post-commit retained config.
    """
    rejections = load_rejections() if comment_rejections else {}
    lines: list[str] = []
    lines.append("system {")
    lines.append("    host-name dut;")
    lines.append("}")
    lines.append("interfaces {")
    lines.append("    lo0 {")
    lines.append("        unit 0 {")
    lines.append("            family inet {")
    lines.append("                address 2.2.2.2/32;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("    ge-0/0/0 {")
    lines.append('        description "link to sender";')
    lines.append("        unit 0 {")
    lines.append("            family inet {")
    lines.append("                address 10.0.12.1/31;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("    ge-0/0/1 {")
    lines.append('        description "link to collector";')
    lines.append("        unit 0 {")
    lines.append("            family inet {")
    lines.append("                address 10.0.23.0/31;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    lines.append("routing-options {")
    lines.append("    autonomous-system 65002;")
    lines.append("    router-id 2.2.2.2;")
    lines.append("}")

    # Class-of-service stubs (forwarding classes, cos-next-hop-maps).
    lines.append("class-of-service {")
    lines.append("    forwarding-classes {")
    lines.append("        class fc1 queue-num 0;")
    lines.append("        class fc2 queue-num 1;")
    lines.append("    }")
    lines.append("    cos-next-hop-map nhm1 {")
    lines.append("        forwarding-class fc1 {")
    lines.append("            next-hop 192.0.2.10;")
    lines.append("        }")
    lines.append("    }")
    lines.append("    cos-next-hop-map nhm2 {")
    lines.append("        forwarding-class fc2 {")
    lines.append("            next-hop 192.0.2.11;")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")

    # Policy-options: communities, source-classes, tunnel-attributes, then the IMPORT policy.
    lines.append("policy-options {")
    lines.append("    /*")
    lines.append(
        "     * §4 community payload definitions (also used as marker communities at sender)."
    )
    lines.append("     *   RED   = 65001:1001  BLUE = 65001:1002")
    lines.append("     *   GREEN = 65001:1003  YELLOW = 65001:1004")
    lines.append("     * §5 flow-control branch markers:")
    lines.append("     *   MARK-A = 65001:9100  MARK-B = 65001:9101")
    lines.append("     */")
    lines.append("    community RED { members 65001:1001; }")
    lines.append("    community BLUE { members 65001:1002; }")
    lines.append("    community GREEN { members 65001:1003; }")
    lines.append("    community YELLOW { members 65001:1004; }")
    lines.append("    community MARK-A { members 65001:9100; }")
    lines.append("    community MARK-B { members 65001:9101; }")

    # Tunnel-attribute stubs.
    lines.append("    tunnel-attribute ta1 {")
    lines.append("        remote-end-point 1.1.1.1;")
    lines.append("        tunnel-type ipip;")
    lines.append("    }")
    lines.append("    tunnel-attribute ta2 {")
    lines.append("        remote-end-point 2.2.2.2;")
    lines.append("        tunnel-type ipip;")
    lines.append("    }")

    # source-class stubs (declared via firewall family inet filter; as a
    # last resort, declared bare under policy-options, which Junos accepts
    # as "no body" entries for source/destination class names that are
    # then referenced by policy actions).
    lines.append("    /*")
    lines.append(
        "     * source-class names referenced by §1 SOURCE-CLASS terms. Declared"
    )
    lines.append(
        "     * here so that `then source-class scN` parses; the actual install"
    )
    lines.append("     * into the SCU/DCU table is not exercised by this lab.")
    lines.append("     */")

    # Now the giant IMPORT policy.
    lines.append("    policy-statement IMPORT {")
    # Group terms by section_label so the file is scannable.
    section_order = ["1", "2", "3", "4", "5", "6", "7"]
    for sec in section_order:
        sec_terms = [t for t in terms if t["section_label"] == sec]
        if not sec_terms:
            continue
        lines.append(
            "        /* ============================================================"
        )
        lines.append(f"         * §{sec}  ({len(sec_terms)} terms)")
        lines.append(
            "         * ============================================================ */"
        )
        for term in sec_terms:
            lines.extend(render_term(term, rejection=rejections.get(term["term_id"])))
    lines.append("        /* Anything not matched is rejected; keeps logs clean. */")
    lines.append("        term REJECT-OTHER {")
    lines.append("            then reject;")
    lines.append("        }")
    lines.append("    }")

    # EXPORT-ALL policy for re-advertising to collector with all attributes.
    lines.append(
        "    /* Pass-through to collector so observation point sees everything. */"
    )
    lines.append("    policy-statement EXPORT-ALL {")
    lines.append("        then accept;")
    lines.append("    }")

    lines.append("}")

    # BGP groups: one inbound from sender, one outbound to collector.
    lines.append("protocols {")
    lines.append("    bgp {")
    lines.append("        group FROM-SENDER {")
    lines.append("            type external;")
    lines.append("            peer-as 65001;")
    lines.append("            neighbor 10.0.12.0 {")
    lines.append("                import IMPORT;")
    lines.append("            }")
    lines.append("        }")
    lines.append("        group TO-COLLECTOR {")
    lines.append("            type external;")
    lines.append("            peer-as 65003;")
    lines.append("            neighbor 10.0.23.1 {")
    lines.append("                export EXPORT-ALL;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")

    return "\n".join(lines) + "\n"


def render_sender_cfg(terms: list[dict]) -> str:
    """Build sender.cfg.

    Sender originates each test prefix as a static discard route, then
    exports it to dut tagged with:
      - the per-term marker community 65001:<term-id>
      - any input-payload communities specified by §4 terms
    """
    lines: list[str] = []
    lines.append("system {")
    lines.append("    host-name sender;")
    lines.append("}")
    lines.append("interfaces {")
    lines.append("    lo0 {")
    lines.append("        unit 0 {")
    lines.append("            family inet {")
    lines.append("                address 1.1.1.1/32;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("    ge-0/0/0 {")
    lines.append('        description "link to dut";')
    lines.append("        unit 0 {")
    lines.append("            family inet {")
    lines.append("                address 10.0.12.0/31;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    lines.append("routing-options {")
    lines.append("    autonomous-system 65001;")
    lines.append("    router-id 1.1.1.1;")
    lines.append("    static {")
    for t in terms:
        lines.append(
            f"        route {t['prefix']} discard;  /* term {t['term_id']} {t['name']} */"
        )
    lines.append("    }")
    lines.append("}")
    lines.append("policy-options {")
    # Payload community names (must match dut for clarity).
    lines.append("    community RED    { members 65001:1001; }")
    lines.append("    community BLUE   { members 65001:1002; }")
    lines.append("    community GREEN  { members 65001:1003; }")
    lines.append("    community YELLOW { members 65001:1004; }")
    # One marker community per term-id.
    lines.append(
        "    /* Per-term marker communities so observation points self-identify each prefix. */"
    )
    for t in terms:
        lines.append(
            f"    community MARK-{t['term_id']} {{ members 65001:{t['term_id']}; }}"
        )

    # EXPORT policy: one term per prefix that adds the marker community plus
    # any input-payload communities, then accepts.
    lines.append("    policy-statement EXPORT-TO-DUT {")
    for t in terms:
        tid = t["term_id"]
        prefix = t["prefix"]
        payload = t.get("input_communities") or []
        lines.append(f"        term TAG-{tid} {{")
        lines.append("            from {")
        lines.append("                protocol static;")
        lines.append(f"                route-filter {prefix} exact;")
        lines.append("            }")
        lines.append("            then {")
        lines.append(f"                community add MARK-{tid};")
        for c in payload:
            lines.append(f"                community add {c};")
        lines.append("                accept;")
        lines.append("            }")
        lines.append("        }")
    lines.append("        /* Reject anything outside the matrix to keep dut clean. */")
    lines.append("        term REJECT-OTHER {")
    lines.append("            then reject;")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    lines.append("protocols {")
    lines.append("    bgp {")
    lines.append("        group TO-DUT {")
    lines.append("            type external;")
    lines.append("            peer-as 65002;")
    lines.append("            neighbor 10.0.12.1 {")
    lines.append("                export EXPORT-TO-DUT;")
    lines.append("            }")
    lines.append("        }")
    lines.append("    }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_master_yaml(terms: list[dict]) -> str:
    """Master metadata table the README will render from."""
    payload = {
        "terms": [
            {
                "term_id": t["term_id"],
                "section": t["section_label"],
                "prefix": t["prefix"],
                "name": t["name"],
                "actions": list(t["actions"]),
                "input_communities": list(t.get("input_communities") or []),
                "description": t.get("description", ""),
            }
            for t in terms
        ]
    }
    header = (
        "# Auto-generated by working/junos-then-action-conflicts/assemble.py.\n"
        "# Master term metadata for the junos_then_action_conflicts lab.\n"
    )
    return header + yaml.safe_dump(payload, sort_keys=False, width=200)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-configs",
        action="store_true",
        help="Also write the FULL dut.cfg/sender.cfg (overwrites minimal). "
        "Used by the FINAL render-from-results step, NOT during the "
        "EC2 commit-iterate phase.",
    )
    args = parser.parse_args()

    terms, stubs = load_terms()
    print(f"Loaded {len(terms)} terms across all sections.")
    by_section: dict[str, int] = {}
    for t in terms:
        by_section[t["section_label"]] = by_section.get(t["section_label"], 0) + 1
    for sec, n in sorted(by_section.items()):
        print(f"  §{sec}: {n} terms")
    (HERE / "term-metadata.yaml").write_text(render_master_yaml(terms))
    print("Wrote term-metadata.yaml.")
    if args.write_configs:
        CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
        (CONFIGS_DIR / "dut.cfg").write_text(render_dut_cfg(terms, stubs))
        (CONFIGS_DIR / "sender.cfg").write_text(render_sender_cfg(terms))
        print(
            "Wrote configs/dut.cfg + configs/sender.cfg (with /* COMMIT-REJECTED */ for rejects)."
        )
        # Also write the "intended" view: every term as live config, no
        # rejection wrapping. This is the pre-collapse visual reference
        # to diff against the post-commit retained config in the snapshot.
        (HERE / "dut.intended.cfg").write_text(
            render_dut_cfg(terms, stubs, comment_rejections=False)
        )
        print(
            "Wrote build/dut.intended.cfg (every term as live config — visual reference)."
        )


if __name__ == "__main__":
    main()
