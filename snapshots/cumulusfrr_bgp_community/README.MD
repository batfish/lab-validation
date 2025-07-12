## LAB Facts

- EBGP configured between two devices `cumulusfrr1 & 2`.
- `cumulusfrr1` is setting community to prefixes before sending it to `cumulusfrr2`
  - `172.16.1.1/32` set community `65001:1`
  - `172.16.1.2/32` set community `65001:2`
  - `172.16.1.2/32` set community `65001:3`
  - `172.16.1.4/32` set community `65001:4`
  - `172.16.1.7/32` set community `65001:7`
- `cumulusfrr2` is checking the community value set by `cumulusfrr1` and take action accordingly
  - match community `65001:1`, no set community, just as-path prepend
  - match community `65001:2`, set new community `65002:2`
  - match community `65001:3`, prepend new community `65002:3` (community additive)
  - match community `65001:4`, prepend new community `65002:4`. `route-map 50` will not match the condition because there is not community named with ``65002:4`. `route-map 60` will match and prepend community `65002:6`
  - match community `65001:7`, set tag `70` & prepend community `65002:7` on `route-map 70`. On `route-map 80` set new tag `80` & prepend new community `65002:8`
  - set `65002:9` for rest of the prefixes
