# Junos `then`-Action Conflict Lab

When a Junos `then` block contains two or more actions targeting the
same attribute, what does the device retain after commit? This lab
empirically characterizes the commit-time collapse behavior for every
`then` action family in `policy-statement` syntax.

## Topology

```
sender (AS 65001) --- dut (AS 65002) --- collector (AS 65003)
       ge-0/0/0  <->  ge-0/0/0  ge-0/0/1  <->  ge-0/0/0
       10.0.12.0      10.0.12.1  10.0.23.0      10.0.23.1
```

Sender originates 112 `/24` test prefixes, each tagged with a unique
marker community `65001:<term-id>`. Dut's import policy has one term
per conflict shape. Collector observes what propagates (§5 flow-control
terms).

## Building

The committed `source/configs/` is the resolved config — every term
accepts and the lab can in principle boot from it directly. The build
infrastructure under `source/build/` (manifests, assembler,
push-terms) is kept anyway for two reasons: (1) it produced the
resolved config in the first place by iterating commit-check failures
back into the manifests, and (2) future expansions of the matrix can
reuse the same probe-then-apply workflow. See `source/build/README.md`
for the exact workflow.

## Running

```
lab_builder validate source/topology.clab.yml --checks source/checks.yaml
```

## Key Findings

Deployed on vJunos-router 25.4R1.12 (containerlab on EC2). Sickbay
entries in `validation/sickbay.yaml` track which Batfish modeling
gaps remain.

### The retained config is canonical, not source-order

For most action families, Junos's hierarchical config tree holds at
most one of each. After commit, `show configuration ... | display set`
emits the actions in a deterministic canonical order (side-effects
first, then terminators; within each, by attribute), regardless of
the order they were written. The author's source order is not
preserved. Two authorings that differ only in source order produce
identical retained config.

Community actions (`community add`/`delete`/`set`) are an exception —
multiple of them in the same `then` block all survive commit and run
sequentially in source order (see below).

### Same-family duplicates: last-wins (or dedup)

For any attribute family where Junos's data model holds at most one
value per route — origin, preference, tag, color, priority, next-hop
(IP form), source-class, external, local-preference, metric, metric2,
load-balance, install-nexthop, the same-family `as-path-prepend×2`
or `as-path-expand×2`, and the named-disposition family containing
both `next term` and `next policy` — when two actions in the same
`then` target the same attribute, the **last action wins** at commit
time and the prior is silently dropped. Identical duplicates collapse
to one (dedup).

Within numeric attributes (lp/metric/metric2), this absorbs every
combination of `set`/`add`/`subtract` and the metric-only `expression`
and `igp` forms: each is treated as the same family, last-wins
(see §2). This generalizes the `junos_rmw_localpref` finding to all
numeric attributes and forms.

### Cross-family at the same attribute: both retained, canonical order

Some attribute families have multiple distinct flavors that Junos
treats independently:

- `as-path-prepend` and `as-path-expand` are different families. Both
  survive commit when both are configured, and the retained order is
  always **prepend before expand**, regardless of source order (see §3
  rows 2004 vs 2005, 2008 vs 2009).
- `tunnel-attribute set X; set Y` (with X ≠ Y) keeps both `set` lines
  in retained config. Runtime semantics — whether both are applied,
  or which one wins — are not observable from this lab's BGP RIB and
  not characterized here.

### `community add/delete/set` are not collapsed at commit

Community statements all survive commit — Junos does not drop any of
them at config time. At runtime they are evaluated sequentially with
their plain meanings: `set` assigns, `add` unions, `delete` removes.
So `community set X; community set Y` ends with `{Y}` because the
second `set` overwrites; `community delete X; community add X` ends
with X present. See §4 results table.

### Flow-control terminators

The `then` block can contain bare `accept`/`reject`, the named
non-terminator dispositions `next term`/`next policy`, and
`default-action accept`/`default-action reject`. These interact at
both commit time and runtime:

**Commit-time:**

1. **Canonical reordering.** Side-effects sort before terminators.
   Among terminators, named forms (`next term`, `next policy`,
   `default-action *`) come before bare `accept`/`reject`. So
   `accept; community add X` retains as `community add X; accept`.
2. **Same-family last-wins among bare terminators.** `accept; reject`
   keeps `reject` only; `reject; accept` keeps `accept` only (§5
   rows 4001, 4002).
3. **`next term` and `next policy` are the same family.** A `then`
   block holds at most one of them: dedup collapses `next term;
next term` to one `next term`, and `next policy; next policy` to
   one `next policy` (rows 4011, 4012). When both forms appear in
   the same `then`, last-wins applies — `next term; next policy`
   retains `next policy`, and `next policy; next term` retains
   `next term` (rows 4013, 4014). The retained line, not the
   author's first line, is what runs.
4. **Different-family pairings.** `default-action accept` paired with
   a bare `accept`/`reject` keeps both lines in retained config; the
   bare terminator wins at runtime. `next term`/`next policy` paired
   with a bare `accept`/`reject` keeps both lines as well; the
   `next term`/`next policy` wins at runtime.

**Runtime ordering** observable from §5's collector RIB:

- Bare `accept` vs bare `reject`: whichever survives commit-time
  collapse fires (rows 4001, 4002).
- `next term` beats bare `accept` regardless of source order — both
  lines exist in retained config but the route falls through (rows
  4003, 4004 do not propagate to collector).
- `next term` (alone or as the surviving NT/NP collapse) jumps to the
  next term, where `REJECT-OTHER` drops the route — no propagation
  to collector (rows 4011, 4014).
- `next policy` (alone or as the surviving NT/NP collapse) returns
  the route to BGP processing; with no further policies, the route
  is accepted and propagates to collector (rows 4012, 4013).
- `default-action *` is overridden by any bare terminator in the same
  `then`. `accept; default-action reject` → route propagates (accept
  fires, default-action reject is a no-op when a terminator already
  ran). `reject; default-action accept` → route rejected. This means
  `default-action` immediately followed by a bare terminator is
  effectively dead config.

Both of those last cases (`default-action` adjacent to a bare
terminator, and any non-logging side-effect in the same `then` as a
bare `reject` — whether before or after the `reject`, since the route
is rejected either way) are dead config on the device. They are
reasonable candidates for a Batfish "risky warning" since they almost
always indicate unintended config.

### Platform-specific syntax requirements

These actions have non-trivial syntactic requirements observable at
commit time:

- `aigp-originate` requires a `next-hop` clause in the same `then`
  block; the test terms include `next-hop self` to satisfy this.
- `cos-next-hop-map NAME` requires `class-of-service forwarding-policy
next-hop-map NAME { ... }` to be defined (not the more obvious
  `class-of-service cos-next-hop-map NAME { ... }`).
- `install-nexthop` requires one of `lsp <name>`, `lsp-regex`,
  `static-lsp <name>`, `static-lsp-regex`, `address <ip>`, or
  `except <ip>`. Bare `install-nexthop strict` is documented as valid
  but commit-rejected on this vJunos-router build (~25.4R1.12).
- `bgp-output-queue-priority`: not valid in policy-statement `then` on
  vJunos-router (MX platform). Silently dropped at load time.

## Results

### §1

| ID  | Prefix     | Name                            | Source `then` actions                                                  | Retained `then` actions                                    | Interpretation                               |
| --- | ---------- | ------------------------------- | ---------------------------------------------------------------------- | ---------------------------------------------------------- | -------------------------------------------- |
| 1   | 10.50.1.0  | ORIGIN-DEDUP                    | origin igp; origin igp                                                 | origin igp; accept                                         | dedup                                        |
| 2   | 10.50.2.0  | ORIGIN-DIFF                     | origin igp; origin egp                                                 | origin egp; accept                                         | last-wins                                    |
| 3   | 10.50.3.0  | PREFERENCE-DEDUP                | preference 100; preference 100                                         | preference 100; accept                                     | dedup                                        |
| 4   | 10.50.4.0  | PREFERENCE-DIFF                 | preference 100; preference 200                                         | preference 200; accept                                     | last-wins                                    |
| 5   | 10.50.5.0  | FORWARDING-CLASS-DEDUP          | forwarding-class fc1; forwarding-class fc1                             | forwarding-class fc1; accept                               | dedup                                        |
| 6   | 10.50.6.0  | FORWARDING-CLASS-DIFF           | forwarding-class fc1; forwarding-class fc2                             | forwarding-class fc2; accept                               | last-wins                                    |
| 7   | 10.50.7.0  | TAG-DEDUP                       | tag 100; tag 100                                                       | tag 100; accept                                            | dedup                                        |
| 8   | 10.50.8.0  | TAG-DIFF                        | tag 100; tag 200                                                       | tag 200; accept                                            | last-wins                                    |
| 9   | 10.50.9.0  | TAG2-DEDUP                      | tag2 100; tag2 100                                                     | tag2 100; accept                                           | dedup                                        |
| 10  | 10.50.10.0 | TAG2-DIFF                       | tag2 100; tag2 200                                                     | tag2 200; accept                                           | last-wins                                    |
| 11  | 10.50.11.0 | COLOR-DEDUP                     | color 100; color 100                                                   | color 100; accept                                          | dedup                                        |
| 12  | 10.50.12.0 | COLOR-DIFF                      | color 100; color 200                                                   | color 200; accept                                          | last-wins                                    |
| 13  | 10.50.13.0 | COLOR2-DEDUP                    | color2 100; color2 100                                                 | color2 100; accept                                         | dedup                                        |
| 14  | 10.50.14.0 | COLOR2-DIFF                     | color2 100; color2 200                                                 | color2 200; accept                                         | last-wins                                    |
| 15  | 10.50.15.0 | PRIORITY-DEDUP                  | priority high; priority high                                           | priority high; accept                                      | dedup                                        |
| 16  | 10.50.16.0 | PRIORITY-DIFF                   | priority high; priority low                                            | priority low; accept                                       | last-wins                                    |
| 17  | 10.50.17.0 | NEXT-HOP-IP-DEDUP               | next-hop 192.0.2.1; next-hop 192.0.2.1                                 | next-hop 192.0.2.1; accept                                 | dedup                                        |
| 18  | 10.50.18.0 | NEXT-HOP-IP-DIFF                | next-hop 192.0.2.1; next-hop 192.0.2.2                                 | next-hop 192.0.2.2; accept                                 | last-wins                                    |
| 19  | 10.50.19.0 | NEXT-HOP-SELF-VS-IP             | next-hop self; next-hop 192.0.2.1                                      | next-hop 192.0.2.1; accept                                 | last-wins                                    |
| 20  | 10.50.20.0 | NEXT-HOP-SELF-VS-PEER           | next-hop self; next-hop peer-address                                   | next-hop peer-address; accept                              | last-wins                                    |
| 21  | 10.50.21.0 | NEXT-HOP-REJECT-VS-DISCARD      | next-hop reject; next-hop discard                                      | next-hop discard; accept                                   | last-wins                                    |
| 22  | 10.50.22.0 | SOURCE-CLASS-DEDUP              | source-class sc1; source-class sc1                                     | source-class sc1; accept                                   | dedup                                        |
| 23  | 10.50.23.0 | SOURCE-CLASS-DIFF               | source-class sc1; source-class sc2                                     | source-class sc2; accept                                   | last-wins                                    |
| 24  | 10.50.24.0 | BGP-OUTPUT-QUEUE-PRIORITY-DEDUP | bgp-output-queue-priority 5; bgp-output-queue-priority 5               | accept                                                     | all dropped at load (platform-not-supported) |
| 25  | 10.50.25.0 | BGP-OUTPUT-QUEUE-PRIORITY-DIFF  | bgp-output-queue-priority 5; bgp-output-queue-priority 10              | accept                                                     | all dropped at load (platform-not-supported) |
| 26  | 10.50.26.0 | COS-NEXT-HOP-MAP-DEDUP          | cos-next-hop-map nhm1; cos-next-hop-map nhm1                           | cos-next-hop-map nhm1; accept                              | dedup                                        |
| 27  | 10.50.27.0 | COS-NEXT-HOP-MAP-DIFF           | cos-next-hop-map nhm1; cos-next-hop-map nhm2                           | cos-next-hop-map nhm2; accept                              | last-wins                                    |
| 28  | 10.50.28.0 | TUNNEL-ATTRIBUTE-DEDUP          | tunnel-attribute set ta1; tunnel-attribute set ta1                     | tunnel-attribute set ta1; accept                           | dedup                                        |
| 29  | 10.50.29.0 | TUNNEL-ATTRIBUTE-DIFF           | tunnel-attribute set ta1; tunnel-attribute set ta2                     | tunnel-attribute set ta1; tunnel-attribute set ta2; accept | all retained                                 |
| 30  | 10.50.30.0 | EXTERNAL-DEDUP                  | external type 1; external type 1                                       | external type 1; accept                                    | dedup                                        |
| 31  | 10.50.31.0 | EXTERNAL-DIFF                   | external type 1; external type 2                                       | external type 2; accept                                    | last-wins                                    |
| 32  | 10.50.32.0 | AIGP-ORIGINATE-DEDUP            | next-hop self; aigp-originate; aigp-originate                          | aigp-originate; next-hop self; accept                      | partial collapse                             |
| 33  | 10.50.33.0 | AIGP-ORIGINATE-BARE-VS-DISTANCE | next-hop self; aigp-originate; aigp-originate distance 50              | aigp-originate distance 50; next-hop self; accept          | partial collapse                             |
| 34  | 10.50.34.0 | AIGP-ORIGINATE-DISTANCE-DEDUP   | next-hop self; aigp-originate distance 50; aigp-originate distance 50  | aigp-originate distance 50; next-hop self; accept          | partial collapse                             |
| 35  | 10.50.35.0 | AIGP-ORIGINATE-DISTANCE-DIFF    | next-hop self; aigp-originate distance 50; aigp-originate distance 100 | aigp-originate distance 100; next-hop self; accept         | partial collapse                             |

### §2

| ID   | Prefix     | Name               | Source `then` actions                                       | Retained `then` actions                                                          | Interpretation                                                                                            |
| ---- | ---------- | ------------------ | ----------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1001 | 10.50.50.0 | LP-SET-DIFF        | local-preference 200; local-preference 50                   | local-preference 50; accept                                                      | last-wins                                                                                                 |
| 1002 | 10.50.51.0 | LP-SET-SAME        | local-preference 200; local-preference 200                  | local-preference 200; accept                                                     | dedup                                                                                                     |
| 1003 | 10.50.52.0 | LP-SET-ADD         | local-preference 200; local-preference add 50               | local-preference add 50; accept                                                  | last-wins                                                                                                 |
| 1004 | 10.50.53.0 | LP-ADD-SET         | local-preference add 50; local-preference 200               | local-preference 200; accept                                                     | last-wins                                                                                                 |
| 1005 | 10.50.54.0 | LP-SET-SUBTRACT    | local-preference 200; local-preference subtract 50          | local-preference subtract 50; accept                                             | last-wins                                                                                                 |
| 1006 | 10.50.55.0 | LP-SUBTRACT-SET    | local-preference subtract 50; local-preference 200          | local-preference 200; accept                                                     | last-wins                                                                                                 |
| 1007 | 10.50.56.0 | LP-ADD-DIFF        | local-preference add 200; local-preference add 50           | local-preference add 50; accept                                                  | last-wins                                                                                                 |
| 1008 | 10.50.57.0 | LP-ADD-SAME        | local-preference add 200; local-preference add 200          | local-preference add 200; accept                                                 | dedup                                                                                                     |
| 1009 | 10.50.58.0 | LP-SUBTRACT-DIFF   | local-preference subtract 200; local-preference subtract 50 | local-preference subtract 50; accept                                             | last-wins                                                                                                 |
| 1010 | 10.50.59.0 | LP-ADD-SUBTRACT    | local-preference add 200; local-preference subtract 50      | local-preference subtract 50; accept                                             | last-wins                                                                                                 |
| 1011 | 10.50.60.0 | MED-SET-DIFF       | metric 200; metric 50                                       | metric 50; accept                                                                | last-wins                                                                                                 |
| 1012 | 10.50.61.0 | MED-SET-SAME       | metric 200; metric 200                                      | metric 200; accept                                                               | dedup                                                                                                     |
| 1013 | 10.50.62.0 | MED-SET-ADD        | metric 200; metric add 50                                   | metric add 50; accept                                                            | last-wins                                                                                                 |
| 1014 | 10.50.63.0 | MED-ADD-SET        | metric add 50; metric 200                                   | metric 200; accept                                                               | last-wins                                                                                                 |
| 1015 | 10.50.64.0 | MED-SET-SUBTRACT   | metric 200; metric subtract 50                              | metric subtract 50; accept                                                       | last-wins                                                                                                 |
| 1016 | 10.50.65.0 | MED-SUBTRACT-SET   | metric subtract 50; metric 200                              | metric 200; accept                                                               | last-wins                                                                                                 |
| 1017 | 10.50.66.0 | MED-ADD-DIFF       | metric add 200; metric add 50                               | metric add 50; accept                                                            | last-wins                                                                                                 |
| 1018 | 10.50.67.0 | MED-ADD-SAME       | metric add 200; metric add 200                              | metric add 200; accept                                                           | dedup                                                                                                     |
| 1019 | 10.50.68.0 | MED-SUBTRACT-DIFF  | metric subtract 200; metric subtract 50                     | metric subtract 50; accept                                                       | last-wins                                                                                                 |
| 1020 | 10.50.69.0 | MED-ADD-SUBTRACT   | metric add 200; metric subtract 50                          | metric subtract 50; accept                                                       | last-wins                                                                                                 |
| 1021 | 10.50.70.0 | MED-SET-EXPRESSION | metric 200; metric expression metric multiplier 2 offset 5  | metric expression metric multiplier 2; metric expression metric offset 5; accept | last-wins (the `metric 200` is dropped; multiplier+offset are subfields of one logical expression action) |
| 1022 | 10.50.71.0 | MED-EXPRESSION-SET | metric expression metric multiplier 2 offset 5; metric 200  | metric 200; accept                                                               | last-wins                                                                                                 |
| 1023 | 10.50.72.0 | MED-SET-IGP        | metric 200; metric igp                                      | metric igp; accept                                                               | last-wins                                                                                                 |
| 1024 | 10.50.73.0 | MED-IGP-SET        | metric igp; metric 200                                      | metric 200; accept                                                               | last-wins                                                                                                 |
| 1025 | 10.50.74.0 | MED-EXPRESSION-IGP | metric expression metric multiplier 2 offset 5; metric igp  | metric igp; accept                                                               | last-wins                                                                                                 |
| 1026 | 10.50.75.0 | M2-SET-DIFF        | metric2 200; metric2 50                                     | metric2 50; accept                                                               | last-wins                                                                                                 |
| 1027 | 10.50.76.0 | M2-SET-SAME        | metric2 200; metric2 200                                    | metric2 200; accept                                                              | dedup                                                                                                     |
| 1028 | 10.50.77.0 | M2-SET-ADD         | metric2 200; metric2 add 50                                 | metric2 add 50; accept                                                           | last-wins                                                                                                 |
| 1029 | 10.50.78.0 | M2-ADD-SET         | metric2 add 50; metric2 200                                 | metric2 200; accept                                                              | last-wins                                                                                                 |
| 1030 | 10.50.79.0 | M2-SET-SUBTRACT    | metric2 200; metric2 subtract 50                            | metric2 subtract 50; accept                                                      | last-wins                                                                                                 |
| 1031 | 10.50.80.0 | M2-SUBTRACT-SET    | metric2 subtract 50; metric2 200                            | metric2 200; accept                                                              | last-wins                                                                                                 |
| 1032 | 10.50.81.0 | M2-ADD-DIFF        | metric2 add 200; metric2 add 50                             | metric2 add 50; accept                                                           | last-wins                                                                                                 |
| 1033 | 10.50.82.0 | M2-ADD-SAME        | metric2 add 200; metric2 add 200                            | metric2 add 200; accept                                                          | dedup                                                                                                     |
| 1034 | 10.50.83.0 | M2-SUBTRACT-DIFF   | metric2 subtract 200; metric2 subtract 50                   | metric2 subtract 50; accept                                                      | last-wins                                                                                                 |
| 1035 | 10.50.84.0 | M2-ADD-SUBTRACT    | metric2 add 200; metric2 subtract 50                        | metric2 subtract 50; accept                                                      | last-wins                                                                                                 |

### §3

| ID   | Prefix      | Name                   | Source `then` actions                                          | Retained `then` actions                                       | Interpretation |
| ---- | ----------- | ---------------------- | -------------------------------------------------------------- | ------------------------------------------------------------- | -------------- |
| 2001 | 10.50.100.0 | PREPEND-DIFF           | as-path-prepend "65010"; as-path-prepend "65020"               | as-path-prepend 65020; accept                                 | last-wins      |
| 2002 | 10.50.101.0 | PREPEND-SAME           | as-path-prepend "65010"; as-path-prepend "65010"               | as-path-prepend 65010; accept                                 | dedup          |
| 2003 | 10.50.102.0 | PREPEND-MULTI-SINGLE   | as-path-prepend "65010 65020"; as-path-prepend "65030"         | as-path-prepend 65030; accept                                 | last-wins      |
| 2004 | 10.50.103.0 | PREPEND-EXPAND-DIFF    | as-path-prepend "65010"; as-path-expand "65020"                | as-path-prepend 65010; as-path-expand 65020; accept           | all retained   |
| 2005 | 10.50.104.0 | EXPAND-PREPEND-DIFF    | as-path-expand "65020"; as-path-prepend "65010"                | as-path-prepend 65010; as-path-expand 65020; accept           | all retained   |
| 2006 | 10.50.105.0 | EXPAND-EXPAND-DIFF     | as-path-expand "65010"; as-path-expand "65020"                 | as-path-expand 65020; accept                                  | last-wins      |
| 2007 | 10.50.106.0 | EXPAND-EXPAND-SAME     | as-path-expand "65010"; as-path-expand "65010"                 | as-path-expand 65010; accept                                  | dedup          |
| 2008 | 10.50.107.0 | EXPAND-LAST-AS-PREPEND | as-path-expand last-as count 2; as-path-prepend "65010"        | as-path-prepend 65010; as-path-expand last-as count 2; accept | all retained   |
| 2009 | 10.50.108.0 | PREPEND-EXPAND-LAST-AS | as-path-prepend "65010"; as-path-expand last-as count 2        | as-path-prepend 65010; as-path-expand last-as count 2; accept | all retained   |
| 2010 | 10.50.109.0 | EXPAND-LAST-AS-TWICE   | as-path-expand last-as count 2; as-path-expand last-as count 3 | as-path-expand last-as count 3; accept                        | last-wins      |

### §4

| ID   | Prefix      | Name                              | Source `then` actions                                                            | Retained `then` actions                                                                  | Interpretation |
| ---- | ----------- | --------------------------------- | -------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | -------------- |
| 3001 | 10.50.130.0 | ADD-RED-ADD-BLUE                  | community add RED; community add BLUE                                            | community add RED; community add BLUE; accept                                            | all retained   |
| 3002 | 10.50.131.0 | ADD-RED-ADD-RED                   | community add RED; community add RED                                             | community add RED; accept                                                                | dedup          |
| 3003 | 10.50.132.0 | DELETE-RED-DELETE-BLUE            | community delete RED; community delete BLUE                                      | community delete RED; community delete BLUE; accept                                      | all retained   |
| 3004 | 10.50.133.0 | SET-RED-ADD-BLUE                  | community set RED; community add BLUE                                            | community set RED; community add BLUE; accept                                            | all retained   |
| 3005 | 10.50.134.0 | ADD-RED-SET-BLUE                  | community add RED; community set BLUE                                            | community add RED; community set BLUE; accept                                            | all retained   |
| 3006 | 10.50.135.0 | SET-RED-SET-BLUE                  | community set RED; community set BLUE                                            | community set RED; community set BLUE; accept                                            | all retained   |
| 3007 | 10.50.136.0 | ADD-RED-DELETE-RED                | community add RED; community delete RED                                          | community add RED; community delete RED; accept                                          | all retained   |
| 3008 | 10.50.137.0 | DELETE-RED-ADD-RED                | community delete RED; community add RED                                          | community delete RED; community add RED; accept                                          | all retained   |
| 3009 | 10.50.138.0 | ADD-RED-DELETE-BLUE               | community add RED; community delete BLUE                                         | community add RED; community delete BLUE; accept                                         | all retained   |
| 3010 | 10.50.139.0 | SET-RED-DELETE-RED                | community set RED; community delete RED                                          | community set RED; community delete RED; accept                                          | all retained   |
| 3011 | 10.50.140.0 | SET-RED-BLUE-DELETE-RED           | community set RED; community set BLUE; community delete RED                      | community set RED; community set BLUE; community delete RED; accept                      | all retained   |
| 3012 | 10.50.141.0 | SET-RED-BLUE-ADD-GREEN            | community set RED; community set BLUE; community add GREEN                       | community set RED; community set BLUE; community add GREEN; accept                       | all retained   |
| 3013 | 10.50.142.0 | SET-RED-BLUE-SET-GREEN-YELLOW     | community set RED; community set BLUE; community set GREEN; community set YELLOW | community set RED; community set BLUE; community set GREEN; community set YELLOW; accept | all retained   |
| 3014 | 10.50.143.0 | SET-RED-BLUE-DESUGAR-VERIFICATION | community set RED; community set BLUE                                            | community set RED; community set BLUE; accept                                            | all retained   |

### §5

| ID   | Prefix      | Name                                 | Source `then` actions                                                     | Retained `then` actions                                                   | Interpretation   |
| ---- | ----------- | ------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------------------------- | ---------------- |
| 4001 | 10.50.160.0 | FC-ACCEPT-THEN-REJECT                | community add MARK-A; accept; community add MARK-B; reject                | community add MARK-A; community add MARK-B; reject                        | all retained     |
| 4002 | 10.50.161.0 | FC-REJECT-THEN-ACCEPT                | community add MARK-A; reject; community add MARK-B; accept                | community add MARK-A; community add MARK-B; accept                        | all retained     |
| 4003 | 10.50.162.0 | FC-ACCEPT-THEN-NEXT-TERM             | community add MARK-A; accept; community add MARK-B; next term             | community add MARK-A; community add MARK-B; next term; accept             | all retained     |
| 4004 | 10.50.163.0 | FC-NEXT-TERM-THEN-ACCEPT             | community add MARK-A; next term; community add MARK-B; accept             | community add MARK-A; community add MARK-B; next term; accept             | all retained     |
| 4005 | 10.50.164.0 | FC-ACCEPT-THEN-NEXT-POLICY           | community add MARK-A; accept; community add MARK-B; next policy           | community add MARK-A; community add MARK-B; next policy; accept           | all retained     |
| 4006 | 10.50.165.0 | FC-DEFAULT-ACTION-ACCEPT-THEN-ACCEPT | community add MARK-A; default-action accept; community add MARK-B; accept | community add MARK-A; community add MARK-B; default-action accept; accept | partial collapse |
| 4007 | 10.50.166.0 | FC-ACCEPT-THEN-DEFAULT-ACTION-REJECT | community add MARK-A; accept; community add MARK-B; default-action reject | community add MARK-A; community add MARK-B; default-action reject; accept | partial collapse |
| 4008 | 10.50.167.0 | FC-REJECT-THEN-DEFAULT-ACTION-ACCEPT | community add MARK-A; reject; community add MARK-B; default-action accept | community add MARK-A; community add MARK-B; default-action accept; reject | partial collapse |
| 4009 | 10.50.168.0 | FC-ACCEPT-THEN-SIDE-EFFECT           | community add MARK-A; accept; community add MARK-B                        | community add MARK-A; community add MARK-B; accept                        | all retained     |
| 4010 | 10.50.169.0 | FC-TWO-SIDE-EFFECTS-THEN-ACCEPT      | community add MARK-A; community add MARK-B; accept                        | community add MARK-A; community add MARK-B; accept                        | all retained     |
| 4011 | 10.50.170.0 | FC-NEXT-TERM-DEDUP                   | community add MARK-A; next term; community add MARK-B; next term          | community add MARK-A; community add MARK-B; next term                     | dedup            |
| 4012 | 10.50.171.0 | FC-NEXT-POLICY-DEDUP                 | community add MARK-A; next policy; community add MARK-B; next policy      | community add MARK-A; community add MARK-B; next policy                   | dedup            |
| 4013 | 10.50.172.0 | FC-NEXT-TERM-THEN-NEXT-POLICY        | community add MARK-A; next term; community add MARK-B; next policy        | community add MARK-A; community add MARK-B; next policy                   | last-wins        |
| 4014 | 10.50.173.0 | FC-NEXT-POLICY-THEN-NEXT-TERM        | community add MARK-A; next policy; community add MARK-B; next term        | community add MARK-A; community add MARK-B; next term                     | last-wins        |

### §6

| ID   | Prefix      | Name                            | Source `then` actions                                            | Retained `then` actions                                          | Interpretation |
| ---- | ----------- | ------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------- | -------------- |
| 5001 | 10.50.180.0 | FWD-LOAD-BALANCE-DUPLICATE-DIFF | load-balance per-packet; load-balance consistent-hash; accept    | load-balance consistent-hash; accept                             | last-wins      |
| 5002 | 10.50.181.0 | FWD-MULTIPATH-RESOLVE-DUPLICATE | multipath-resolve; multipath-resolve; accept                     | accept; multipath-resolve                                        | dedup          |
| 5003 | 10.50.182.0 | FWD-INSTALL-NEXTHOP-DIFF        | install-nexthop lsp lsp-foo; install-nexthop lsp lsp-bar; accept | install-nexthop lsp lsp-foo; install-nexthop lsp lsp-bar; accept | all retained   |

### §7

| ID   | Prefix      | Name                   | Source `then` actions                                       | Retained `then` actions                                     | Interpretation |
| ---- | ----------- | ---------------------- | ----------------------------------------------------------- | ----------------------------------------------------------- | -------------- |
| 9001 | 10.50.250.0 | SANITY-CROSS-ATTRIBUTE | local-preference 200; metric 100; community add RED; accept | metric 100; local-preference 200; community add RED; accept | all retained   |

## Companion Data

- **Source configs (post-push, full)**:
  `source/configs/{dut,sender,collector}.cfg` — what the lab device
  actually loaded. Any commit-rejected terms would be preserved as
  `/* COMMIT-REJECTED */` comment blocks (none on the current
  vJunos-router build; the BGP-OUTPUT-QUEUE-PRIORITY actions are
  dropped at load time, not commit time, so the term itself commits
  with only its `accept` surviving).
- **Bootstrap configs (minimal)**:
  `source/build/bootstrap/{dut,sender,collector}.cfg` — what
  containerlab boots with. The full IMPORT/EXPORT terms are pushed
  post-boot via `source/build/push-terms.py`.
- **Build inputs**: `source/build/manifest-N-*.yaml`,
  `source/build/term-metadata.yaml`, `source/build/commit-results.yaml`.
  See `source/build/README.md` for the build workflow.
- **Retained config (collected from device)**:
  `configs/dut/show_configuration_|_display_set.txt`
