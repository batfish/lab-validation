##LAB Facts

- Lab is configured with `vlan 10` with no active members
- `port-channel` is shutdown so that there will be no active members in vlan 10. Physical ports `E1/1 & E1/2` are not shutdown but because of `port-channel` is down, they will be treated as down interfaces
- In real world, vlan with no active member should have state down and hence should not make entry in routing table
