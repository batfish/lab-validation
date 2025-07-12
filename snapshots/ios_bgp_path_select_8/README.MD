## LAB Facts

- Lab is created to test/understand `step 8` of the bgp path selection algorithm, see this: https://www.cisco.com/c/en/us/support/docs/ip/border-gateway-protocol-bgp/13753-25.html
- `leaf` connects to two `spines` via `ebgp`
- Two `spines` connects to `low_igp_metric_8` via `ibgp`. underlay is `ospf`
- When doing traceroute from `low_igp_metric_8(192.168.123.4) --> leaf1(192.168.123.1)` the default path will be via `spine1`; However, in this lab, we are making `spine1` more expensive(by increasing `ospf(IGP)` cost) and hence `spine2` will be the preferred way.
