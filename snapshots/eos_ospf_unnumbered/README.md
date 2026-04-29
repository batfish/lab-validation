A 3-node spine-leaf OSPF lab using Arista cEOS with unnumbered point-to-point
interfaces (`ip address unnumbered Loopback0`).

```
leaf1 (10.0.1.1) ---[Ethernet1]---[Ethernet1]--- spine (10.0.0.1) ---[Ethernet2]---[Ethernet1]--- leaf2 (10.0.2.1)
```

All point-to-point links borrow their IP address from Loopback0 via
`ip address unnumbered`. OSPF forms adjacencies and distributes all loopback
routes. Directly-connected OSPF neighbors appear as interface-only routes;
remote peers use the intermediate router's loopback as the next-hop.

Related issue: https://github.com/batfish/batfish/issues/7227
