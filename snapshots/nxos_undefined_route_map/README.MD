## LAB Facts

- This lab is created to understand the undefined route-map behaviour in Cisco nxos
- There are 2 devices, d1 & d2
- 7 ebgp peering is running between two device to represent below 7 route-map scenarios
  - normal defined, template-peer NA
  - normal NA, template-peer defined
  - normal undefined, template-peer NA
  - normal NA, template-peer undefined
  - normal undefined, template-peer defined
  - normal defined, template-peer undefined
  - normal defined, template-peer defined
  - **_Note:_**
    - `normal` refers to route-map defined/undefined/NA(Not Applicable) at neighbor level, e.g.
      ```
      neighbor 10.12.11.1
          remote-as 65001
          address-family ipv4 unicast
              route-map normal_defined_tp_na in
      ```
    - `template-peer` refers to the route-map is defined/undefined/NA(Not Applicable) at template-peer level, e.g.
      ```
      template peer normal_na_tp_defined
          remote-as 65001
          address-family ipv4 unicast
              route-map normal_na_tp_defined in
      ```
- `1st bgp peering` sends prefix `172.16.1.1/32` from `d1` to `d2` and then `d2` evalute using `route-map`. Same thing happends for rest of the 6 peering; e.g. 2nd peering = `172.16.1.2/32`, 3rd peering = `172.16.1.3/32` and so on.

## Observation

- `route-map` defined at `neighbor-level` will take precedence over `template-level`
- `undefined route-map` will deny everything
