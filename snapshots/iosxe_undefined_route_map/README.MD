## LAB Facts

- This lab is created to understand the undefined route-map behaviour in Cisco IOS
- There are three devices: d1, d2_in & d3_out
- 7 ebgp peering is running between `d1 & d2` which represent below 7 route-map scenarios for in(import) testing
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
      neighbor 10.12.22.1 peer-group normal_na_pg_defined
      ```
    - `template-peer` refers to the route-map is defined/undefined/NA(Not Applicable) at peer-group level, e.g.
      ```
      neighbor normal_undefined_pg_defined peer-group
      neighbor normal_undefined_pg_defined remote-as 65001
      neighbor 10.12.55.1 peer-group normal_undefined_pg_defined
      address-family ipv4
        neighbor normal_undefined_pg_defined route-map normal_undefined_pg_defined in
      ```
- `1st bgp peering` sends prefix `172.16.1.1/32` from `d1` to `d2` and then `d2` evalute using `route-map`. Same thing happends for rest of the 6 peering; e.g. 2nd peering = `172.16.1.2/32`, 3rd peering = `172.16.1.3/32` and so on.
- 4 ebgp peering is running between `d1 & d3` which represent below 4 route-map scenarios for out(export) testing - normal defined, peer-group NA - normal NA, peer-group defined - normal undefined, peer-group NA - normal NA, peer-group undefined
  **Note:** IOS does not allow to configure `route-map` at `neibhbor level`, if the neighbor is part of the `peer-group` i.e. `route-map` has to be at `peer-group` level. It will throw the error `% Invalid command for a peer-group member`. Because of this limitation, we have four scenarios in out direction instead of 7.

## Observation

- `route-map` defined at `neighbor-level` will take precedence over `template-level`
- `undefined route-map` will deny everything
