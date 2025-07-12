![Topology](eos_ospf_bgp_.png)

### LAB Facts

This lab is to test BGP Aggregate routes injected as OSPF(E2) to a neighbor in OSPF.

1. np01 and np02 are iBGP peers.
2. np01 & np02 have a static route 10.203.0.0/24 in RIB table.
3. np01 & np02 summarizing the static route as 10.203.0.0/16
4. np01 & np02 connected to dlh15 and running OSPF in Area 0
5. np01 & np02 are redistributing the aggregate netwrok 10.203.0.0/16 into OSPF.
6. dlh15 receives the 10.203.0.0/16 as OSPF E2

Conclusion:
dlh15 will prefer OSPF E2 routes from the lowest router-id (OSPF) from np01, then dlh15 will propagate this route to np02. Since E2 route received by np02 with a better AD (110), np02 will remove BGP aggregate from it's BGP table.
