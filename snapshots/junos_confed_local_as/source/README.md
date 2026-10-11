# junos_confed_local_as

Four vJunos routers. r1 is a member of BGP confederation 7 (sub-AS 65001)
and uses `local-as 65100` on two external groups. The lab records what
Junos does with a group whose local-as is outside the confederation:
whether the session is plain eBGP, which ASes end up in the path, and
how routes cross the confederation border in each direction.

Reference: batfish/batfish#10418 (session type), #10420, #10421, #10422
(findings below).

## Topology

```
r2 (AS 7)              --[ge-0/0/0]--[ge-0/0/0]-- r1 (AS 65001, confederation 7)
  lo0 10.2.2.2/32        10.0.12.1    10.0.12.0    lo0 10.1.1.1/32
r3 (AS 65002, confed 7) --[ge-0/0/0]--[ge-0/0/1]-- r1
  lo0 10.3.3.3/32        10.0.13.1    10.0.13.0
r4 (AS 65200)          --[ge-0/0/0]--[ge-0/0/2]-- r1
  lo0 10.4.4.4/32        10.0.14.1    10.0.14.0
```

Each router originates one static /24 (10.N0.1.0/24 for rN). r1 also
exports its direct routes so that r3 can resolve next hops that
confederation eBGP leaves unchanged.

r1's groups:

| group          | peer       | config                                                   |
| -------------- | ---------- | -------------------------------------------------------- |
| CONFED         | r3 (65002) | `type external; peer-as 65002`                           |
| EXTERNAL       | r2 (7)     | `peer-as 7; local-as 65100 private no-prepend-global-as` |
| EXTERNAL-PLAIN | r4 (65200) | `peer-as 65200; local-as 65100`                          |

r2 and r4 peer with AS 65100.

## Findings (vJunos-router 25.4R1.12)

All three sessions establish. The two local-as sessions behave as plain
eBGP: no confederation segments, local preference not carried, next hop
set to self.

AS paths r1 sends, by route origin:

| route from   | to r2 (`private no-prepend-global-as`) | to r4 (plain `local-as`) | to r3 (confederation) |
| ------------ | -------------------------------------- | ------------------------ | --------------------- |
| r1 itself    | `65100`                                | `65100`                  | (empty)               |
| r3 `(65002)` | `65100`                                | `65100 7`                | n/a                   |
| r4 `65200`   | `65100 65200`                          | n/a                      | `65100 65200`         |

- Confederation segments never leave the confederation. Without
  `no-prepend-global-as` the confederation AS 7 takes their place; with
  it they are dropped.
- The global AS is not prepended for r1's own routes on either local-as
  group. Only the local-as 65100 is.
- A route learned over the plain local-as group carries 65100 when
  re-advertised inside the confederation (`(65001) 65100 65200` at r3),
  even though r1's own RIB shows it as `65200`.
- r2's route 10.20.1.0/24 arrives at r1 with AS path `7` and is hidden:
  7 is r1's confederation identifier, so Junos treats it as a loop.
  Nothing from AS 7 enters the confederation.

## Batfish

With batfish/batfish#10418, Batfish types the r1-r2 and r1-r4 sessions as
single-hop eBGP with local AS 65100 and establishes all sessions. Three
differences remain, each sickbayed to its issue:

- batfish/batfish#10420: Batfish accepts 10.20.1.0/24 (path `7`) on r1
  and re-advertises it to r3 and r4. Its loop check only looks for the
  session's local AS.
- batfish/batfish#10421: Batfish sends `65100 (65002)` to both r2 and
  r4; the confederation segment should be removed (and replaced by 7
  for r4).
- batfish/batfish#10422: Batfish sends `(65001) 65200` to r3 for the
  route learned from r4, without the 65100.

## Build notes

- The lab builder's `push-config` commits the change but then times out
  waiting for the Junos prompt, printing a netmiko error. The config is
  applied; verify with `show configuration` before retrying.
- Junos `export` is a list, so `set protocols bgp group X export NEW`
  appends to an existing export policy instead of replacing it. Delete
  the old export first.
