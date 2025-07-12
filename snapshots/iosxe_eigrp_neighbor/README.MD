## LAB Facts

- EIGRP is configured between `iosxe1 & 2` to understand EIGRP peering & metric calculation with below different scenarios:
  - Gi1
    - peering via physical ethernet port
  - port-channel23
    - peering via port-channel
  - Gi4
    - peering in vrf_100
- On `iosxe1` EIGRP peering via `Gi4` is using `distribute-list` `out & in` to filter out 172.16.100.1/32 & 172.16.100.2/32 respectively.
