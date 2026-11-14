# junos_policy_tag2

Three vJunos routers. dut (AS 200) sets `tag2` in its BGP import policy
and in the first policy of an export chain, and its export to rx accepts
routes only by `from tag2`. The lab records whether tag2 set on import is
seen by the export policy, whether a later policy in a chain sees a tag2
set by an earlier one, and whether tag2 is sent to the peer. It covers BGP
routes only.

Reference: batfish/batfish#10486 (converts `from tag2` and `then tag2`;
stacked on #10485, which adds tag2 to BGP routes).

## Topology

```
src (AS 65010) ge-0/0/0 10.0.1.0/31 -- dut ge-0/0/0 10.0.1.1/31
rx (AS 300)    ge-0/0/0 10.0.2.1/31 -- dut ge-0/0/1 10.0.2.0/31
```

src originates 10.110.1.0/24 through 10.110.4.0/24.

dut's policies:

| policy        | where                        | what                                                             |
| ------------- | ---------------------------- | ---------------------------------------------------------------- |
| `IMPORT-TAG2` | import from src              | tag2 100 on 10.110.1.0/24, tag2 200 on 10.110.2.0/24, accept all |
| `SET-TAG2`    | export to rx, first in chain | tag2 400 on 10.110.3.0/24, no terminating action                 |
| `MATCH-TAG2`  | export to rx, second         | accept tag2 100 and tag2 400; reject the rest                    |

rx's import policy rejects routes with tag2 100 and accepts the rest, so
10.110.1.0/24 is missing at rx if dut's tag2 reached it.

## Expected routes at rx

| prefix        | tag2 at dut      | at rx if Junos behaves as documented |
| ------------- | ---------------- | ------------------------------------ |
| 10.110.1.0/24 | 100 (import)     | yes, path `200 65010`                |
| 10.110.2.0/24 | 200 (import)     | no                                   |
| 10.110.3.0/24 | 400 (`SET-TAG2`) | yes, if a later policy sees the tag2 |
| 10.110.4.0/24 | none             | no                                   |

## Batfish

Batfish on master does not model tag2: `from tag2` makes its term match
nothing and `then tag2` is ignored, so rx gets no routes from dut. With
batfish/batfish#10486, Batfish matches every row.

## Findings (vJunos-router 26.2R1.7)

rx has 10.110.1.0/24 and 10.110.3.0/24 (path `200 65010`); dut advertises
2 routes. So:

- An export policy matches the tag2 that dut's import policy set.
- A later policy in an export chain matches the tag2 an earlier one set.
- tag2 is not sent to the peer: rx's `from tag2 100 then reject` does not
  reject 10.110.1.0/24.
