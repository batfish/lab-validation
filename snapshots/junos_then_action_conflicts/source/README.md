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

Sender originates 108 `/24` test prefixes, each tagged with a unique
marker community `65001:<term-id>`. Dut's import policy has one term
per conflict shape. Collector observes what propagates (§5 flow-control
terms).

## Running

```
lab_builder validate topology.clab.yml --checks checks.yaml
```

## Key Findings

Deployed 2026-05-20 on vJunos-router 25.4R1.12 (containerlab on EC2).
All 12 checks passed; 15/19 lab tests pass, 4 xfailed (sickbay).

### The universal rule: last-wins

For **all scalar and numeric attributes**, when two actions of the same
kind appear in one `then` block, Junos silently drops the first at
commit time and retains only the last. Identical duplicate actions are
deduplicated to one.

This extends the finding from `junos_rmw_localpref`: it is not specific
to the `set`-vs-arithmetic conflict. ANY two same-family actions
targeting the same attribute are resolved by last-wins at commit time.

### Exceptions to last-wins

| Category                                       | Behavior                                                           |
| ---------------------------------------------- | ------------------------------------------------------------------ |
| `community add/delete/set`                     | All retained — community actions are cumulative, not conflicting   |
| `as-path-prepend` + `as-path-expand`           | Different families — both retained                                 |
| `as-path-prepend` × 2                          | Same family — last-wins                                            |
| `as-path-expand` × 2                           | Same family — last-wins                                            |
| `tunnel-attribute set X; set Y`                | Both retained (different referenced objects)                       |
| `metric expression`                            | Retained as sub-components (multiplier + offset on separate lines) |
| Flow-control (`accept`, `reject`, `next term`) | Terminators are reordered/collapsed — see §5                       |

### Platform-specific notes

- `bgp-output-queue-priority`: not valid in policy-statement `then` on
  vJunos-router (MX platform). Silently dropped at load time.
- `cos-next-hop-map`: requires referenced map object. Our stubs were
  not included in the minimal boot config; commit-rejected.
- `aigp-originate`: requires a `next-hop` clause in the same `then`
  block. Commit-rejected without it.
- `install-nexthop`: requires mandatory address/lsp/etc arguments.
  Commit-rejected.

## Results

### §1

| ID  | Prefix     | Name                            | Source actions                                            | Retained                                           | Interpretation  |
| --- | ---------- | ------------------------------- | --------------------------------------------------------- | -------------------------------------------------- | --------------- |
| 1   | 10.50.1.0  | ORIGIN-DEDUP                    | origin igp; origin igp                                    | origin igp                                         | dedup           |
| 2   | 10.50.2.0  | ORIGIN-DIFF                     | origin igp; origin egp                                    | origin egp                                         | last-wins       |
| 3   | 10.50.3.0  | PREFERENCE-DEDUP                | preference 100; preference 100                            | preference 100                                     | dedup           |
| 4   | 10.50.4.0  | PREFERENCE-DIFF                 | preference 100; preference 200                            | preference 200                                     | last-wins       |
| 5   | 10.50.5.0  | FORWARDING-CLASS-DEDUP          | forwarding-class fc1; forwarding-class fc1                | forwarding-class fc1                               | dedup           |
| 6   | 10.50.6.0  | FORWARDING-CLASS-DIFF           | forwarding-class fc1; forwarding-class fc2                | forwarding-class fc2                               | last-wins       |
| 7   | 10.50.7.0  | TAG-DEDUP                       | tag 100; tag 100                                          | tag 100                                            | dedup           |
| 8   | 10.50.8.0  | TAG-DIFF                        | tag 100; tag 200                                          | tag 200                                            | last-wins       |
| 9   | 10.50.9.0  | TAG2-DEDUP                      | tag2 100; tag2 100                                        | tag2 100                                           | dedup           |
| 10  | 10.50.10.0 | TAG2-DIFF                       | tag2 100; tag2 200                                        | tag2 200                                           | last-wins       |
| 11  | 10.50.11.0 | COLOR-DEDUP                     | color 100; color 100                                      | color 100                                          | dedup           |
| 12  | 10.50.12.0 | COLOR-DIFF                      | color 100; color 200                                      | color 200                                          | last-wins       |
| 13  | 10.50.13.0 | COLOR2-DEDUP                    | color2 100; color2 100                                    | color2 100                                         | dedup           |
| 14  | 10.50.14.0 | COLOR2-DIFF                     | color2 100; color2 200                                    | color2 200                                         | last-wins       |
| 15  | 10.50.15.0 | PRIORITY-DEDUP                  | priority high; priority high                              | priority high                                      | dedup           |
| 16  | 10.50.16.0 | PRIORITY-DIFF                   | priority high; priority low                               | priority low                                       | last-wins       |
| 17  | 10.50.17.0 | NEXT-HOP-IP-DEDUP               | next-hop 192.0.2.1; next-hop 192.0.2.1                    | next-hop 192.0.2.1                                 | dedup           |
| 18  | 10.50.18.0 | NEXT-HOP-IP-DIFF                | next-hop 192.0.2.1; next-hop 192.0.2.2                    | next-hop 192.0.2.2                                 | last-wins       |
| 19  | 10.50.19.0 | NEXT-HOP-SELF-VS-IP             | next-hop self; next-hop 192.0.2.1                         | next-hop 192.0.2.1                                 | last-wins       |
| 20  | 10.50.20.0 | NEXT-HOP-SELF-VS-PEER           | next-hop self; next-hop peer-address                      | next-hop peer-address                              | last-wins       |
| 21  | 10.50.21.0 | NEXT-HOP-REJECT-VS-DISCARD      | next-hop reject; next-hop discard                         | next-hop discard                                   | last-wins       |
| 22  | 10.50.22.0 | SOURCE-CLASS-DEDUP              | source-class sc1; source-class sc1                        | source-class sc1                                   | dedup           |
| 23  | 10.50.23.0 | SOURCE-CLASS-DIFF               | source-class sc1; source-class sc2                        | source-class sc2                                   | last-wins       |
| 24  | 10.50.24.0 | BGP-OUTPUT-QUEUE-PRIORITY-DEDUP | bgp-output-queue-priority 5; bgp-output-queue-priority 5  | (none)                                             | all-dropped     |
| 25  | 10.50.25.0 | BGP-OUTPUT-QUEUE-PRIORITY-DIFF  | bgp-output-queue-priority 5; bgp-output-queue-priority 10 | (none)                                             | all-dropped     |
| 26  | 10.50.26.0 | COS-NEXT-HOP-MAP-DEDUP          | cos-next-hop-map nhm1; cos-next-hop-map nhm1              | (rejected)                                         | commit-rejected |
| 27  | 10.50.27.0 | COS-NEXT-HOP-MAP-DIFF           | cos-next-hop-map nhm1; cos-next-hop-map nhm2              | (rejected)                                         | commit-rejected |
| 28  | 10.50.28.0 | TUNNEL-ATTRIBUTE-DEDUP          | tunnel-attribute set ta1; tunnel-attribute set ta1        | tunnel-attribute set ta1                           | dedup           |
| 29  | 10.50.29.0 | TUNNEL-ATTRIBUTE-DIFF           | tunnel-attribute set ta1; tunnel-attribute set ta2        | tunnel-attribute set ta1; tunnel-attribute set ta2 | all-retained    |
| 30  | 10.50.30.0 | EXTERNAL-DEDUP                  | external type 1; external type 1                          | external type 1                                    | dedup           |
| 31  | 10.50.31.0 | EXTERNAL-DIFF                   | external type 1; external type 2                          | external type 2                                    | last-wins       |
| 32  | 10.50.32.0 | AIGP-ORIGINATE-DEDUP            | aigp-originate; aigp-originate                            | (rejected)                                         | commit-rejected |
| 33  | 10.50.33.0 | AIGP-ORIGINATE-BARE-VS-DISTANCE | aigp-originate; aigp-originate distance 50                | (rejected)                                         | commit-rejected |
| 34  | 10.50.34.0 | AIGP-ORIGINATE-DISTANCE-DEDUP   | aigp-originate distance 50; aigp-originate distance 50    | (rejected)                                         | commit-rejected |
| 35  | 10.50.35.0 | AIGP-ORIGINATE-DISTANCE-DIFF    | aigp-originate distance 50; aigp-originate distance 100   | (rejected)                                         | commit-rejected |

### §2

| ID   | Prefix     | Name               | Source actions                                              | Retained                                                                 | Interpretation |
| ---- | ---------- | ------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------ | -------------- |
| 1001 | 10.50.50.0 | LP-SET-DIFF        | local-preference 200; local-preference 50                   | local-preference 50                                                      | last-wins      |
| 1002 | 10.50.51.0 | LP-SET-SAME        | local-preference 200; local-preference 200                  | local-preference 200                                                     | dedup          |
| 1003 | 10.50.52.0 | LP-SET-ADD         | local-preference 200; local-preference add 50               | local-preference add 50                                                  | last-wins      |
| 1004 | 10.50.53.0 | LP-ADD-SET         | local-preference add 50; local-preference 200               | local-preference 200                                                     | last-wins      |
| 1005 | 10.50.54.0 | LP-SET-SUBTRACT    | local-preference 200; local-preference subtract 50          | local-preference subtract 50                                             | last-wins      |
| 1006 | 10.50.55.0 | LP-SUBTRACT-SET    | local-preference subtract 50; local-preference 200          | local-preference 200                                                     | last-wins      |
| 1007 | 10.50.56.0 | LP-ADD-DIFF        | local-preference add 200; local-preference add 50           | local-preference add 50                                                  | last-wins      |
| 1008 | 10.50.57.0 | LP-ADD-SAME        | local-preference add 200; local-preference add 200          | local-preference add 200                                                 | dedup          |
| 1009 | 10.50.58.0 | LP-SUBTRACT-DIFF   | local-preference subtract 200; local-preference subtract 50 | local-preference subtract 50                                             | last-wins      |
| 1010 | 10.50.59.0 | LP-ADD-SUBTRACT    | local-preference add 200; local-preference subtract 50      | local-preference subtract 50                                             | last-wins      |
| 1011 | 10.50.60.0 | MED-SET-DIFF       | metric 200; metric 50                                       | metric 50                                                                | last-wins      |
| 1012 | 10.50.61.0 | MED-SET-SAME       | metric 200; metric 200                                      | metric 200                                                               | dedup          |
| 1013 | 10.50.62.0 | MED-SET-ADD        | metric 200; metric add 50                                   | metric add 50                                                            | last-wins      |
| 1014 | 10.50.63.0 | MED-ADD-SET        | metric add 50; metric 200                                   | metric 200                                                               | last-wins      |
| 1015 | 10.50.64.0 | MED-SET-SUBTRACT   | metric 200; metric subtract 50                              | metric subtract 50                                                       | last-wins      |
| 1016 | 10.50.65.0 | MED-SUBTRACT-SET   | metric subtract 50; metric 200                              | metric 200                                                               | last-wins      |
| 1017 | 10.50.66.0 | MED-ADD-DIFF       | metric add 200; metric add 50                               | metric add 50                                                            | last-wins      |
| 1018 | 10.50.67.0 | MED-ADD-SAME       | metric add 200; metric add 200                              | metric add 200                                                           | dedup          |
| 1019 | 10.50.68.0 | MED-SUBTRACT-DIFF  | metric subtract 200; metric subtract 50                     | metric subtract 50                                                       | last-wins      |
| 1020 | 10.50.69.0 | MED-ADD-SUBTRACT   | metric add 200; metric subtract 50                          | metric subtract 50                                                       | last-wins      |
| 1021 | 10.50.70.0 | MED-SET-EXPRESSION | metric 200; metric expression metric multiplier 2 offset 5  | metric expression metric multiplier 2; metric expression metric offset 5 | all-retained   |
| 1022 | 10.50.71.0 | MED-EXPRESSION-SET | metric expression metric multiplier 2 offset 5; metric 200  | metric 200                                                               | last-wins      |
| 1023 | 10.50.72.0 | MED-SET-IGP        | metric 200; metric igp                                      | metric igp                                                               | last-wins      |
| 1024 | 10.50.73.0 | MED-IGP-SET        | metric igp; metric 200                                      | metric 200                                                               | last-wins      |
| 1025 | 10.50.74.0 | MED-EXPRESSION-IGP | metric expression metric multiplier 2 offset 5; metric igp  | metric igp                                                               | last-wins      |
| 1026 | 10.50.75.0 | M2-SET-DIFF        | metric2 200; metric2 50                                     | metric2 50                                                               | last-wins      |
| 1027 | 10.50.76.0 | M2-SET-SAME        | metric2 200; metric2 200                                    | metric2 200                                                              | dedup          |
| 1028 | 10.50.77.0 | M2-SET-ADD         | metric2 200; metric2 add 50                                 | metric2 add 50                                                           | last-wins      |
| 1029 | 10.50.78.0 | M2-ADD-SET         | metric2 add 50; metric2 200                                 | metric2 200                                                              | last-wins      |
| 1030 | 10.50.79.0 | M2-SET-SUBTRACT    | metric2 200; metric2 subtract 50                            | metric2 subtract 50                                                      | last-wins      |
| 1031 | 10.50.80.0 | M2-SUBTRACT-SET    | metric2 subtract 50; metric2 200                            | metric2 200                                                              | last-wins      |
| 1032 | 10.50.81.0 | M2-ADD-DIFF        | metric2 add 200; metric2 add 50                             | metric2 add 50                                                           | last-wins      |
| 1033 | 10.50.82.0 | M2-ADD-SAME        | metric2 add 200; metric2 add 200                            | metric2 add 200                                                          | dedup          |
| 1034 | 10.50.83.0 | M2-SUBTRACT-DIFF   | metric2 subtract 200; metric2 subtract 50                   | metric2 subtract 50                                                      | last-wins      |
| 1035 | 10.50.84.0 | M2-ADD-SUBTRACT    | metric2 add 200; metric2 subtract 50                        | metric2 subtract 50                                                      | last-wins      |

### §3

| ID   | Prefix      | Name                   | Source actions                                                 | Retained                                              | Interpretation |
| ---- | ----------- | ---------------------- | -------------------------------------------------------------- | ----------------------------------------------------- | -------------- |
| 2001 | 10.50.100.0 | PREPEND-DIFF           | as-path-prepend "65010"; as-path-prepend "65020"               | as-path-prepend 65020                                 | last-wins      |
| 2002 | 10.50.101.0 | PREPEND-SAME           | as-path-prepend "65010"; as-path-prepend "65010"               | as-path-prepend 65010                                 | dedup          |
| 2003 | 10.50.102.0 | PREPEND-MULTI-SINGLE   | as-path-prepend "65010 65020"; as-path-prepend "65030"         | as-path-prepend 65030                                 | last-wins      |
| 2004 | 10.50.103.0 | PREPEND-EXPAND-DIFF    | as-path-prepend "65010"; as-path-expand "65020"                | as-path-prepend 65010; as-path-expand 65020           | all-retained   |
| 2005 | 10.50.104.0 | EXPAND-PREPEND-DIFF    | as-path-expand "65020"; as-path-prepend "65010"                | as-path-prepend 65010; as-path-expand 65020           | all-retained   |
| 2006 | 10.50.105.0 | EXPAND-EXPAND-DIFF     | as-path-expand "65010"; as-path-expand "65020"                 | as-path-expand 65020                                  | last-wins      |
| 2007 | 10.50.106.0 | EXPAND-EXPAND-SAME     | as-path-expand "65010"; as-path-expand "65010"                 | as-path-expand 65010                                  | dedup          |
| 2008 | 10.50.107.0 | EXPAND-LAST-AS-PREPEND | as-path-expand last-as count 2; as-path-prepend "65010"        | as-path-prepend 65010; as-path-expand last-as count 2 | all-retained   |
| 2009 | 10.50.108.0 | PREPEND-EXPAND-LAST-AS | as-path-prepend "65010"; as-path-expand last-as count 2        | as-path-prepend 65010; as-path-expand last-as count 2 | all-retained   |
| 2010 | 10.50.109.0 | EXPAND-LAST-AS-TWICE   | as-path-expand last-as count 2; as-path-expand last-as count 3 | as-path-expand last-as count 3                        | last-wins      |

### §4

| ID   | Prefix      | Name                              | Source actions                                                                   | Retained                                                                         | Interpretation |
| ---- | ----------- | --------------------------------- | -------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | -------------- |
| 3001 | 10.50.130.0 | ADD-RED-ADD-BLUE                  | community add RED; community add BLUE                                            | community add RED; community add BLUE                                            | all-retained   |
| 3002 | 10.50.131.0 | ADD-RED-ADD-RED                   | community add RED; community add RED                                             | community add RED                                                                | dedup          |
| 3003 | 10.50.132.0 | DELETE-RED-DELETE-BLUE            | community delete RED; community delete BLUE                                      | community delete RED; community delete BLUE                                      | all-retained   |
| 3004 | 10.50.133.0 | SET-RED-ADD-BLUE                  | community set RED; community add BLUE                                            | community set RED; community add BLUE                                            | all-retained   |
| 3005 | 10.50.134.0 | ADD-RED-SET-BLUE                  | community add RED; community set BLUE                                            | community add RED; community set BLUE                                            | all-retained   |
| 3006 | 10.50.135.0 | SET-RED-SET-BLUE                  | community set RED; community set BLUE                                            | community set RED; community set BLUE                                            | all-retained   |
| 3007 | 10.50.136.0 | ADD-RED-DELETE-RED                | community add RED; community delete RED                                          | community add RED; community delete RED                                          | all-retained   |
| 3008 | 10.50.137.0 | DELETE-RED-ADD-RED                | community delete RED; community add RED                                          | community delete RED; community add RED                                          | all-retained   |
| 3009 | 10.50.138.0 | ADD-RED-DELETE-BLUE               | community add RED; community delete BLUE                                         | community add RED; community delete BLUE                                         | all-retained   |
| 3010 | 10.50.139.0 | SET-RED-DELETE-RED                | community set RED; community delete RED                                          | community set RED; community delete RED                                          | all-retained   |
| 3011 | 10.50.140.0 | SET-RED-BLUE-DELETE-RED           | community set RED; community set BLUE; community delete RED                      | community set RED; community set BLUE; community delete RED                      | all-retained   |
| 3012 | 10.50.141.0 | SET-RED-BLUE-ADD-GREEN            | community set RED; community set BLUE; community add GREEN                       | community set RED; community set BLUE; community add GREEN                       | all-retained   |
| 3013 | 10.50.142.0 | SET-RED-BLUE-SET-GREEN-YELLOW     | community set RED; community set BLUE; community set GREEN; community set YELLOW | community set RED; community set BLUE; community set GREEN; community set YELLOW | all-retained   |
| 3014 | 10.50.143.0 | SET-RED-BLUE-DESUGAR-VERIFICATION | community set RED; community set BLUE                                            | community set RED; community set BLUE                                            | all-retained   |

### §5

| ID   | Prefix      | Name                                 | Source actions                                                            | Retained                                                                  | Interpretation |
| ---- | ----------- | ------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------------------------- | -------------- |
| 4001 | 10.50.160.0 | FC-ACCEPT-THEN-REJECT                | community add MARK-A; accept; community add MARK-B; reject                | community add MARK-A; community add MARK-B; reject                        |                |
| 4002 | 10.50.161.0 | FC-REJECT-THEN-ACCEPT                | community add MARK-A; reject; community add MARK-B; accept                | community add MARK-A; community add MARK-B                                | all-retained   |
| 4003 | 10.50.162.0 | FC-ACCEPT-THEN-NEXT-TERM             | community add MARK-A; accept; community add MARK-B; next term             | community add MARK-A; community add MARK-B; next term                     |                |
| 4004 | 10.50.163.0 | FC-NEXT-TERM-THEN-ACCEPT             | community add MARK-A; next term; community add MARK-B; accept             | community add MARK-A; community add MARK-B; next term                     |                |
| 4005 | 10.50.164.0 | FC-ACCEPT-THEN-NEXT-POLICY           | community add MARK-A; accept; community add MARK-B; next policy           | community add MARK-A; community add MARK-B; next policy                   |                |
| 4006 | 10.50.165.0 | FC-DEFAULT-ACTION-ACCEPT-THEN-ACCEPT | community add MARK-A; default-action accept; community add MARK-B; accept | community add MARK-A; community add MARK-B; default-action accept         | all-retained   |
| 4007 | 10.50.166.0 | FC-ACCEPT-THEN-DEFAULT-ACTION-REJECT | community add MARK-A; accept; community add MARK-B; default-action reject | community add MARK-A; community add MARK-B; default-action reject         | all-retained   |
| 4008 | 10.50.167.0 | FC-REJECT-THEN-DEFAULT-ACTION-ACCEPT | community add MARK-A; reject; community add MARK-B; default-action accept | community add MARK-A; community add MARK-B; default-action accept; reject |                |
| 4009 | 10.50.168.0 | FC-ACCEPT-THEN-SIDE-EFFECT           | community add MARK-A; accept; community add MARK-B                        | community add MARK-A; community add MARK-B                                | all-retained   |
| 4010 | 10.50.169.0 | FC-TWO-SIDE-EFFECTS-THEN-ACCEPT      | community add MARK-A; community add MARK-B; accept                        | community add MARK-A; community add MARK-B                                | all-retained   |

### §6

| ID   | Prefix      | Name                            | Source actions                                                | Retained                     | Interpretation  |
| ---- | ----------- | ------------------------------- | ------------------------------------------------------------- | ---------------------------- | --------------- |
| 5001 | 10.50.180.0 | FWD-LOAD-BALANCE-DUPLICATE-DIFF | load-balance per-packet; load-balance consistent-hash; accept | load-balance consistent-hash | last-wins       |
| 5002 | 10.50.181.0 | FWD-MULTIPATH-RESOLVE-DUPLICATE | multipath-resolve; multipath-resolve; accept                  | multipath-resolve            | dedup           |
| 5003 | 10.50.182.0 | FWD-INSTALL-NEXTHOP-DIFF        | install-nexthop strict; install-nexthop except; accept        | (rejected)                   | commit-rejected |

### §7

| ID   | Prefix      | Name                   | Source actions                                              | Retained                                            | Interpretation |
| ---- | ----------- | ---------------------- | ----------------------------------------------------------- | --------------------------------------------------- | -------------- |
| 9001 | 10.50.250.0 | SANITY-CROSS-ATTRIBUTE | local-preference 200; metric 100; community add RED; accept | metric 100; local-preference 200; community add RED | all-retained   |

## Companion Data

- Source configs: `snapshots/junos_then_action_conflicts/source/configs/`
- Retained-config snapshot:
  `snapshots/junos_then_action_conflicts/configs/dut/show_configuration_|_display_set.txt`
- Commit-check results:
  `working/junos-then-action-conflicts/commit-results.yaml`
- Term metadata:
  `working/junos-then-action-conflicts/term-metadata.yaml`
