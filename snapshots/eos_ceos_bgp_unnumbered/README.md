A two-node eBGP lab on Arista cEOS using BGP unnumbered (RFC 5549).

```
spine (AS 65000) ---[Ethernet1]---[Ethernet1]--- leaf (AS 65001)
                 ---[Ethernet2]---[Ethernet2]---
  Loopback0: 10.0.0.1/32                           Loopback0: 10.0.0.2/32
```

The two point-to-point links between `spine` and `leaf` have no IPv4
or IPv6 address configured on them — each side uses the `neighbor
interface <range>` syntax to peer over interface IPv6 link-locals,
with IPv4 unicast carried as the RFC 5549 address family.

`maximum-paths 2 ecmp 2` is enabled on both routers so that both
parallel links are active simultaneously and each router's loopback
is reachable via ECMP across `Ethernet1` and `Ethernet2`.
