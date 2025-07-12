## LAB Facts

- EIGRP is configured between `nxos1 & 2` to understand EIGRP peering & metric calculation under below different scenarios:
  - ethernet1/1
    - peering via physical ethernet port
  - vlan 23
    - peering via L2 port-channel
  - port-channel45.10
    - peering via L3 port-channel sub interface
- On `nxos1` EIGRP peering via `ethernet1/1` is using `distribute-list` `out & in` to filter out 172.16.100.1/32 & 172.16.100.2/32 respectively.
