## LAB Facts

- This lab is created to understand the undefined route-map behaviour in Cisco IOS
- There are three devices: d1, d2_in & d3_out
- 7 ebgp peering is running between `(d1,d2) & (d1,d3)` which represent below 7 route-map scenarios
  - normal defined, peer-group NA
  - normal NA, peer-group defined
  - normal undefined, peer-group NA
  - normal NA, peer-group undefined
  - normal undefined, peer-group defined
  - normal defined, peer-group undefined
  - normal defined, peer-group defined
  - **_Note:_**
    - `normal` refers to route-map defined/undefined/NA(Not Applicable) at neighbor level, e.g.
      ```
      neighbor 10.13.11.1 route-map normal_defined_pg_na out
      ```
    - `peer-group` refers to the route-map is defined/undefined/NA(Not Applicable) at peer-group level, e.g.
      ```
      neighbor 10.13.22.1 peer-group normal_na_pg_defined
      neighbor normal_na_pg_defined remote-as 65001
      neighbor normal_na_pg_defined route-map normal_na_pg_defined out
      neighbor normal_na_pg_defined maximum-routes 12000
      ```
- IN(import) between `d1 & d2`: `1st bgp peering` sends prefix `172.16.1.1/32` from `d1` to `d2` and then `d2` evalute using `route-map`. Same thing happends for rest of the 6 peering; e.g. 2nd peering = `172.16.1.2/32`, 3rd peering = `172.16.1.3/32` and so on
- OUT(export) between `d1 & d3`: `1st bgp peering` sends prefix `172.16.3.1/32` from `d3` to `d1`. `d3` evalute using `route-map` before sending it to `d1`. Same thing happends for rest of the 6 peering; e.g. 2nd peering = `172.16.3.2/32`, 3rd peering = `172.16.3.3/32` and so on

## Observation

- `route-map` defined at `neighbor-level` will take precedence over `peer-level`
- `undefined` route-map will permit everything
