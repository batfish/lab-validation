# junos_policy_color

Three vJunos routers. dut (AS 200) sets `color` and `color2` in its BGP
import policy and `color` in the first policy of an export chain, and its
export to rx accepts routes only by `from color` and `from color2`. The
lab records whether an export policy matches the color and color2 that
import set, whether a later policy in a chain matches a color set by an
earlier one, and whether color is sent to the peer. It covers BGP routes
only.

## Topology

```
src (AS 65010) ge-0/0/0 10.0.1.0/31 -- dut ge-0/0/0 10.0.1.1/31
rx (AS 300)    ge-0/0/0 10.0.2.1/31 -- dut ge-0/0/1 10.0.2.0/31
```

src originates 10.130.1.0/24 through 10.130.4.0/24.

dut's policies:

| policy         | where                        | what                                                                |
| -------------- | ---------------------------- | ------------------------------------------------------------------- |
| `IMPORT-COLOR` | import from src              | color 100 on 10.130.1.0/24, color2 200 on 10.130.2.0/24, accept all |
| `SET-COLOR`    | export to rx, first in chain | color 400 on 10.130.3.0/24, no terminating action                   |
| `MATCH-COLOR`  | export to rx, second         | accept color 100, color2 200 and color 400; reject the rest         |

rx's import policy rejects routes with color 100 and accepts the rest, so
10.130.1.0/24 is missing at rx if dut's color reached it.

## Expected routes at rx

| prefix        | at dut                  | at rx if Junos behaves like tag2 |
| ------------- | ----------------------- | -------------------------------- |
| 10.130.1.0/24 | color 100 (import)      | yes, path `200 65010`            |
| 10.130.2.0/24 | color2 200 (import)     | yes, path `200 65010`            |
| 10.130.3.0/24 | color 400 (`SET-COLOR`) | yes, if a later policy sees it   |
| 10.130.4.0/24 | none                    | no                               |

## Findings (vJunos-router 26.2R1.7)

rx has 10.130.1.0/24, 10.130.2.0/24 and 10.130.3.0/24 (path `200 65010`);
dut advertises 3 routes. So color and color2 behave like tag2:

- An export policy matches the color and color2 that dut's import policy
  set.
- A later policy in an export chain matches a color an earlier one set.
- Color is not sent to the peer: rx's `from color 100 then reject` does
  not reject 10.130.1.0/24.

## Batfish

On master before batfish/batfish#10490 (batfish/batfish#10488), `from
color` made the data plane computation fail, `from color2` was not
parsed, and `then color` and `then color2` were ignored. With
batfish/batfish#10490 (stacked on #10489, which adds color and color2 to
BGP routes), Batfish matches every route.
