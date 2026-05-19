# Junos Community Delete Lab

Does `community delete ALL-COMMUNITIES` with `members .*:.*` actually remove
**all** community types from a BGP route?

## Hypothesis

The regex `.*:.*` requires a colon character. Well-known communities like
`no-export`, `no-advertise`, and `no-export-subconfed` are represented as
keywords, not `ASN:value` pairs. They may not match, and therefore survive
the delete.

## Topology

```
sender (AS 65001) --- dut (AS 65002) --- collector (AS 65003)
       ge-0/0/0  <->  ge-0/0/0  ge-0/0/1  <->  ge-0/0/0
       10.0.12.0      10.0.12.1 10.0.23.0      10.0.23.1
```

## Test Routes

sender originates these static routes and tags each with a specific community
via export policy:

| Prefix       | Community Applied         | Type                      |
| ------------ | ------------------------- | ------------------------- |
| 10.10.0.0/24 | (none)                    | control                   |
| 10.10.1.0/24 | 65001:100                 | standard                  |
| 10.10.2.0/24 | no-export                 | well-known standard       |
| 10.10.3.0/24 | no-advertise              | well-known standard       |
| 10.10.4.0/24 | no-export-subconfed       | well-known standard       |
| 10.10.5.0/24 | target:65001:200          | extended (route-target)   |
| 10.10.6.0/24 | origin:65001:300          | extended (site-of-origin) |
| 10.10.7.0/24 | large:65001:1:1           | large                     |
| 10.10.8.0/24 | all of the above combined | kitchen sink              |

## DUT Policy

```junos
community ALL-COMMUNITIES members .*:.*;
policy-statement STRIP-COMMUNITIES {
    term STRIP {
        then {
            community delete ALL-COMMUNITIES;
            accept;
        }
    }
}
```

Applied as import policy on the session with sender.

## What to Observe

### On dut

All 9 routes should be present in `inet.0`. Check communities on each route:

- If the delete worked fully, routes should have no communities
- If well-known communities survived, `10.10.2.0/24`, `10.10.3.0/24`,
  `10.10.4.0/24` will still carry them

### On collector

If `no-export` survived the delete on dut, `10.10.2.0/24` will NOT be
advertised to collector (no-export prevents eBGP advertisement).

If `no-advertise` survived, `10.10.3.0/24` will NOT be advertised at all.

If `no-export-subconfed` survived, `10.10.4.0/24` may or may not appear
depending on AS relationship.

The control route (`10.10.0.0/24`) and standard community route
(`10.10.1.0/24`) should always reach collector regardless.

### Key Commands for Manual Inspection

```
# Check communities on routes at dut
show route protocol bgp community detail | display json

# Check which routes reach collector
show route protocol bgp | display json   (on collector)
```
