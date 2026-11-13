# junos_bgp_remove_private

Five vJunos routers. dut (AS 200) has a bare `remove-private` (no
modifiers) on three groups: eBGP to a public AS, eBGP to a private AS,
and iBGP. The lab records which private ASes Junos removes from the
paths it sends, and answers what the Junos documentation leaves open:

1. Does `remove-private` run before or after the group's export policy?
   (An export `as-path-prepend` of a private AS survives only if it runs
   before.)
2. Does it apply to iBGP groups?
3. When the path contains the peer's AS, is nothing removed, or are
   private ASes removed up to the peer's AS?

Reference: batfish/batfish#10480 (converts bare `remove-private`).

## Topology

```
src (AS 65010)    ge-0/0/0 10.0.1.0/31 -- dut ge-0/0/0 10.0.1.1/31
rx300 (AS 300)    ge-0/0/0 10.0.2.1/31 -- dut ge-0/0/1 10.0.2.0/31
rx65030 (AS 65030) ge-0/0/0 10.0.3.1/31 -- dut ge-0/0/2 10.0.3.0/31
ribgp (AS 200)    ge-0/0/0 10.0.4.1/31 -- dut ge-0/0/3 10.0.4.0/31
```

src originates 10.100.1.0/24 through 10.100.8.0/24 with path `65010`.
dut's import policy `SHAPE-PATHS` prepends ASes to five of them (an
import prepend goes to the left of the received path). dut applies policy
`EXPORT` to every receiver group (`[ NEXT-HOP-SELF EXPORT ]` on iBGP).
`EXPORT` prepends 65099 to 10.100.7.0/24 and 400 to 10.100.8.0/24.
rx300 and rx65030 use `autonomous-system N loops 2` so that they keep
paths that contain their own AS.

## Expected AS paths

`junos_private_asn` shows (vJunos 17.4) that Junos removes private ASes
from the left up to the first public AS or the peer's AS: a route with
path `65111 65101 65100` reaches a peer in AS 65100 as `2345 65100`.
The table gives the paths that rule predicts.

| prefix        | path at dut               | rx300                 | rx65030                 | ribgp, if it applies to iBGP |
| ------------- | ------------------------- | --------------------- | ----------------------- | ---------------------------- |
| 10.100.1.0/24 | `65010`                   | `200`                 | `200`                   | (empty)                      |
| 10.100.2.0/24 | `65011 100 65010`         | `200 100 65010`       | `200 100 65010`         | `100 65010`                  |
| 10.100.3.0/24 | `100 65011 65010`         | `200 100 65011 65010` | `200 100 65011 65010`   | `100 65011 65010`            |
| 10.100.4.0/24 | `65011 300 65010`         | `200 300 65010`       | `200 300 65010`         | `300 65010`                  |
| 10.100.5.0/24 | `65011 100 300 65010`     | `200 100 300 65010`   | `200 100 300 65010`     | `100 300 65010`              |
| 10.100.6.0/24 | `65011 65030 65012 65010` | `200`                 | `200 65030 65012 65010` | (empty)                      |

What the rows distinguish:

- 10.100.1-3: where removal stops (first public AS).
- 10.100.4-5 at rx300: the peer's public AS is in the path. The Junos
  documentation also says "If the AS path contains the AS number of the
  EBGP neighbor, BGP does not remove the private AS number"; if that
  holds, rx300 sees `200 65011 300 65010` and `200 65011 100 300 65010`.
- 10.100.6 at rx65030: the peer's private AS is in the path (the
  `junos_private_asn` case).
- ribgp column: if `remove-private` does not apply to iBGP, ribgp sees
  dut's paths unchanged.

10.100.7.0/24 and 10.100.8.0/24 (path `65010` at dut) show where
removal runs relative to the export policy. Junos puts an eBGP export
prepend to the left of its own AS (`junos_private_asn`: AS 65100 with
`as-path-prepend 65101` sends `65101 65100`).

| removal runs                          | 10.100.7 at rx300 | 10.100.8 at rx300 | 10.100.7 at ribgp | 10.100.8 at ribgp |
| ------------------------------------- | ----------------- | ----------------- | ----------------- | ----------------- |
| before the export policy              | `65099 200`       | `400 200`         | `65099`           | `400`             |
| on the final path, after the prepends | `200 65010`       | `400 200 65010`   | (empty)           | `400 65010`       |
| not at all on iBGP                    | n/a               | n/a               | `65099 65010`     | `400 65010`       |

## Findings (vJunos-router 26.2R1.7)

AS paths observed:

| prefix        | rx300                 | rx65030               | ribgp             |
| ------------- | --------------------- | --------------------- | ----------------- |
| 10.100.1.0/24 | `200`                 | `200`                 | (empty)           |
| 10.100.2.0/24 | `200 100 65010`       | `200 100 65010`       | `100 65010`       |
| 10.100.3.0/24 | `200 100 65011 65010` | `200 100 65011 65010` | `100 65011 65010` |
| 10.100.4.0/24 | (not sent)            | `200 300 65010`       | `300 65010`       |
| 10.100.5.0/24 | `200 100 300 65010`   | `200 100 300 65010`   | `100 300 65010`   |
| 10.100.6.0/24 | `200`                 | (not sent)            | (empty)           |
| 10.100.7.0/24 | `65099 200`           | `65099 200`           | `65099`           |
| 10.100.8.0/24 | `400 200`             | `400 200`             | `400`             |

- Removal stops at the first public AS or the peer's AS, as the table
  above expected. The peer's AS later in the path does not stop removal
  before it (10.100.5 at rx300).
- `remove-private` applies to iBGP groups.
- It runs before the export policy: the export prepends of 65099 and
  400 survive, and 65010 is gone from 10.100.8.0/24.
- dut advertises 7 routes to each eBGP receiver
  (`show bgp neighbor`). When removal leaves the peer's AS first in the
  path (10.100.4 toward AS 300, 10.100.6 toward AS 65030), Junos does not
  send the route: without `advertise-peer-as`, Junos does not advertise a
  route whose path, after removal, starts with the peer's AS.
- The export prepend goes to the left of dut's own AS (`65099 200`).

## Batfish

batfish/batfish#10480 converts bare `remove-private`. With it, Batfish
matches every path above except:

- 10.100.7.0/24 and 10.100.8.0/24 at rx300 and rx65030: Batfish puts an
  eBGP export prepend to the right of the local AS (`200 65099`).
  batfish/lab-validation#41.
- 10.100.4.0/24 at rx300 and 10.100.6.0/24 at rx65030: Batfish checks
  the peer's AS against the path before `remove-private`, so it sends
  them. batfish/batfish#10482.

At ribgp, Batfish with #10480 matches every row. The ribgp comparison relies on the
Junos validator comparing AS paths of iBGP routes, which needs the
detail form of `show route protocol bgp` (peer AS and local AS).
