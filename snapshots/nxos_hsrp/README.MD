##LAB Facts

- `hsrp` configured on both nxos devices (`nxos1`, `nxos2`)
- `vlan10` is hsrp vlan
- ibgp peering between two devices
- Both devices will generate `hsrp` route `10.10.10.3/32` in main rib which is `hsrp vip` ip
