## LAB Facts

- This lab is created to understand the redistribution between different routing protocols in Cisco IOSXE
- There are 5 devices D1 to D5.
- Each device represents one routing protocol i.e. `D3_eigrp` represent the the `EIGRP` routing protocol
- `D1_redist` is the central device where all other devices connects as an neighbor and redistribution is happening between all protocols
- Testing the redistribution for following protocols
  - connected
  - static
  - eigrp
  - bgp
  - ospf
- Redistribution is restricted with `route-map`

## Lab Topology

![](Topology.png)
