Experiment lab that measures the effective default values Arista EOS
assigns to locally-originated BGP paths for the best-path-selection
attributes. Each test router both originates and receives the same
prefixes from r-upstream; different inbound route-map perturbations
on the received side force a tiebreak at one specific best-path step
per prefix. The device's "Not best: ..." reason reveals which
attribute actually decided.

```
r-upstream (AS 100)
  Loopback100 10.100.0.100/24   originates 10.100.0.0/24
  Loopback200 10.200.0.100/24   originates 10.200.0.0/24
  Loopback101 10.101.0.100/24   originates 10.101.0.0/24
  Loopback102 10.102.0.100/24   originates 10.102.0.0/24
  Ethernet1 10.0.1.1/31 ------+
  Ethernet2 10.0.2.1/31 --+    \
                          |     \
                          v      v
          r-ribd (AS 300, ribd)  r-ma (AS 200, multi-agent)
          same config patterns on both; each has a matching Loopback
          for every prefix and a `network <prefix>` statement for it.
```

## Experiments

Each test router has a PEER_IN inbound route-map that sets different
attributes on specific received prefixes, making exactly one attribute
the deciding step of best-path selection per prefix.

| Prefix        | Inbound nudge to received path                                           | Best-path step being tested                           |
| ------------- | ------------------------------------------------------------------------ | ----------------------------------------------------- |
| 10.100.0.0/24 | `set weight 10000`                                                       | Default effective weight of a local path              |
| 10.200.0.0/24 | `set weight 10000` + local has `route-map SET_WEIGHT_50000` on `network` | Whether route-map `set weight` applies to local paths |
| 10.101.0.0/24 | `set local-preference 50`                                                | Default effective local-preference (is it >50?)       |
| 10.102.0.0/24 | `set local-preference 150`                                               | Default effective local-preference (is it <150?)      |

## Results (EOS 4.36, both agent modes)

- **10.100.0.0/24**: received (weight 10000) wins. Device emits "Not
  best: Path weight" on the local path. So **local weight default =
  0**, not the oft-assumed 32768.
- **10.200.0.0/24**: local (weight 50000) wins. Route-map `set weight`
  does take effect on a `network` statement.
- **10.101.0.0/24**: local wins. Device emits "Not best: Local
  preference" on the received path. So local's effective local-pref > 50.
- **10.102.0.0/24**: received (localpref 150) wins. Device emits "Not
  best: Local preference" on the local path. So local's effective
  local-pref < 150.
- Combined: **local local-preference default = 100** (the standard BGP
  default), not 0.

See [issue #152](https://github.com/batfish/lab-validation/issues/152)
for the broader implications: Batfish's current Arista model applies
weight 32768 and local-preference 0 to locally-originated paths. Both
are wrong, and together they cause the `test_bgp_rib_routes` failures
sickbayed across many EOS labs.
