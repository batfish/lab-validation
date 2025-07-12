## LAB Facts

- This is a lab that we are using as an `example-network` in Notebooks
- Four BGP AS (1,2,3 & 65001)
- BGP AS 1,2 & 3 runs OSPF as IGP
- Each AS has `RR` configured
  - AS1 = as1core1
  - AS2 = as2core1 & as2core2
  - AS3 = as13core1
- BGP feature `additiona-paths` & `maximum-paths(ebgp)` is configured to get the multiple paths
- Various misconfiguration throughout the lab but high level gotcha are:
  - `as2core2` has broken `ospf neighborship` with `as2border1, as2border2 & as2dist2` due to `MTU` mismatch. Only working neighbor is `as2dist1`
  - `as2core2` has undefined route-map `filter-bogons` for `bgp in` so no `bgp` routes will make in
  - `as1border1` has two `ebgp neighbor` with no peer available
    - bad-ebgp
    - xanadu
  - `as3` internal network `3.0.1.0/24  & 3.0.2.0/24 ` are being advertised by all `as3` devices using `network statement` and as a result BGP rib will have three entries for internal networks
    - `as3border1`
      ```
       * ia3.0.1.0/24       3.10.1.1                 0    100      0 i
      *>                   0.0.0.0                  0         32768 i
      * ia3.0.2.0/24       3.2.2.2                  0    100      0 i
      * ia                 3.10.1.1                 0    100      0 i
      *>                   3.0.1.2                  2         32768 i
      ```
    - `as3border2`
      ```
       * ia3.0.1.0/24       3.1.1.1                  0    100      0 i
      * ia                 3.10.1.1                 0    100      0 i
      *>                   3.0.2.2                  2         32768 i
      * ia3.0.2.0/24       3.10.1.1                 0    100      0 i
      *>                   0.0.0.0                  0         32768 i
      ```
