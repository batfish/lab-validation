# junos_bgp_color_selection

Three vJunos routers. a (AS 65001) and b (AS 65002) originate the same six
/24s to dut (AS 200). dut's import policies set `preference`,
`local-preference`, `color` and `color2` per prefix. The active route at
dut for each prefix shows whether `color` and `color2` take part in BGP
route selection and where they rank.

The Junos documentation says only that color and color2 are preference
values "finer-grained than those specified in the preference and
preference2" conditions, and that "a lower number indicates a more
preferred route".

## Topology

```
a (AS 65001, router ID 10.255.0.1) ge-0/0/0 10.0.1.0/31 -- dut ge-0/0/0 10.0.1.1/31
b (AS 65002, router ID 10.255.0.2) ge-0/0/0 10.0.2.0/31 -- dut ge-0/0/1 10.0.2.1/31
```

dut uses `path-selection external-router-id`, so when every attribute is
equal, the path from a (lower router ID) wins.

## What each prefix tests

| prefix        | from a                            | from b                            | active path if color/color2 work as preference tie-breakers |
| ------------- | --------------------------------- | --------------------------------- | ----------------------------------------------------------- |
| 10.150.1.0/24 | —                                 | —                                 | a (baseline: router ID)                                     |
| 10.150.2.0/24 | `color 200`                       | `color 100`                       | b                                                           |
| 10.150.3.0/24 | `local-preference 200; color 200` | `local-preference 100; color 100` | b if color ranks before local-preference, else a            |
| 10.150.4.0/24 | `color 100; color2 200`           | `color 100; color2 100`           | b                                                           |
| 10.150.5.0/24 | `color 100; color2 100`           | `color 200; color2 50`            | a if color ranks before color2                              |
| 10.150.6.0/24 | `preference 160; color 200`       | `preference 170; color 100`       | a if preference ranks before color                          |

If color and color2 do not affect selection, every prefix goes to a
(10.150.3.0/24 on local-preference, 10.150.6.0/24 on preference, the rest
on router ID).

## Findings (vJunos-router 26.2R1.7)

Color and color2 do not take part in BGP path selection. a's path is
active for every prefix, and b's is inactive with:

| prefix        | b's inactive reason |
| ------------- | ------------------- |
| 10.150.1.0/24 | Router ID           |
| 10.150.2.0/24 | Router ID           |
| 10.150.3.0/24 | Local Preference    |
| 10.150.4.0/24 | Router ID           |
| 10.150.5.0/24 | Router ID           |
| 10.150.6.0/24 | Route Preference    |

The policy lab `junos_policy_color` shows that the import policy does set
color and color2 (an export `from color` matches them), so they are
present on these routes and ignored by selection.

Not covered: whether color breaks ties between routes of different
protocols with equal preference.

## Batfish

Batfish ignores color and color2 (`then color` and `then color2` are not
converted), which matches selection here: every test passes on master.
