##LAB Facts

- Lab is created to test/understand ibgp route propagation/split-horizon rule(Don't get confused with IGP split-hotizon, see this: https://www.oreilly.com/library/view/ccnp-routing-and/9780133149906/ch18lev3sec14.xhtml#:~:text=The%20BGP%20split%2Dhorizon%20rule,the%20reason%20for%20missing%20routes)
- Three devices(D1, D2 & D3) connected via `ibgp` and peering is not full-mesh that means connection is like: `D1 <--> D2 <--> D3`
- Each device advertise one prefix in bgp whch is `172.16.0.1, 2 & 3` corresponds to D1, D2 & D3
- In real world, prefix advertise via D1(172.16.0.1) will be advertise to D2 but D2 will not advertise it to D3. Same thing will happen for prefix advertisment from D3 --> D1. D2 will receive prefix from both D1 & D3
