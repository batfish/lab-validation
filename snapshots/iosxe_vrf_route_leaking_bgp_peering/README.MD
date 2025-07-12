## Topology

![Topology](topology.png)

## LAB Facts

- Lab is created to understand the behavior of vrf leaked route when it is forwarded to `bgp peer`
- 5 devices
  - `d1_v12`
    - two vrfs, `vrf1 & 2`
    - `192.168.123.1/32`, `192.168.123.2/32`
    - `vrf1` has no bgp peering
    - `vrf2` has bgp peering with `d2` & `d44`
  - `d2_v34`
    - two vrfs, `vrf3 & 4`
    - `192.168.123.3/32`, `192.168.123.4/32`
    - `vrf3` has bgp peering with `d33`
  - `d33_v3`
    - one vrfs, `vrf3`
    - `192.168.123.33/32`
  - `d44_default`
    - one vrfs, `default`
    - `192.168.123.44/32`
    - `default` has bgp peering with `d55`
  - `d55_default`
    - one vrfs, `default`
    - `192.168.123.55/32`
- There are two possibilites related to bgp peering. `bgp` peer could be in:
  - `non-default` vrf
    - This is being tested with `d1, d2 & d33`
    - packet flow
      - `d1` has `192.168.123.1/32` in `vrf1`. it is being exported to `vrf2`. `vrf2` forwards it to `d2`
      - `d2` receives it in `vrf3` and export with new `extended RT community 65002:33`.
      - `d33 vrf3` receives it, strip the `extended RT community 65002:33` and install it as valid best.
  - `default` vrf
    - This is being tested with `d1, d44 & d55`
    - packet flow
      - `d1` has `192.168.123.1/32` in `vrf1`. it is being exported to `vrf2`. `vrf2` forwards it to `d44`
      - `d44` receives it in `default vrf` and keep the `extended RT community 65001:11` and forward it to `d55`
      - `d44` tags the community `4:4` (this is different then `extended RT community 65001:11`) to all routes going from `d44` to `d55`
      - `d55` has incoming `route-map COM_IN` which will do following
        - change `local-preference` to `110` for the routes tags with `extended RT community 65001:11`
        - change `local-preference` to `120` for the routes tags with `community 4:4`

## Observation

- bgp peering with
  - `non-default vrf:` peer receives it, strip the `Extended Community: RT` value. We may set new `Extended Community: RT` value using `export` command if needed.
  - `default vrf:` peer receives it and keep the `Extended Community: RT` value and keep on forwarding to the next bgp peers
