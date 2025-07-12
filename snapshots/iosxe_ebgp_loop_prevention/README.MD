## Topology

![Topology](topology.png)

## LAB Facts

- Lab is created to understand the `ebgp loop prevention` in `cisco ios`
  - `d1` advertises two prefixes(`192.168.123.1/32 & 192.168.122.0/24`) to `d2`
  - `d2` receives it and do the following
    - 192.168.123.1/32: prepanding `222` coming in
    - 192.168.122.0/24: no change
  - `d2` then sends it to `d3`. Additionally, `d2` will also advertise `192.168.123.2/32` to `d3`
  - `d3` receives all the routes from `d2`. Rejects the routes(`192.168.123.1/32 & 192.168.122.0/24`) that has `d3's ASN` in `AS-PATH` attribute.
    - logs
    ```
    *Jan 26 18:53:21.058: BGP(0): 10.23.21.1 rcv UPDATE about 192.168.122.0/24 -- DENIED due to: AS-PATH contains our own AS;
    *Jan 26 18:53:21.059: BGP(0): 10.23.21.1 rcv UPDATE about 192.168.123.1/32 -- DENIED due to: AS-PATH contains our own AS;
    d3_iosxe#
    ```
  - `d4` receives all the routes from `d2`. Unlink `d3`, `d4` is configured with `allowas-in`. Hence, routes(`192.168.123.1/32 & 192.168.122.0/24`) will be accepted even though `d3's ASN` in `AS-PATH` attribute.
- 4 devices
  - d1
    - ASN: 65001
  - d2
    - ASN: 65002
  - d3
    - ASN: 65001
  - d4
    - ASN: 65001

## Observation

- BGP sender will send route to peer irrespective of the `AS-PATH` value
- BGP receiver
  - Normal: will reject it if `AS` is present(anywhere) in `AS-PATH`
  - With `allowas-in`: will accept all the routes even though `AS` is present(anywhere) in `AS-PATH`
