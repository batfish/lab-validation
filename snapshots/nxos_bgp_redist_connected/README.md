## Topology

![Topology](Topology.png)

## LAB Facts

- lab is crated to test the redistribution for `local & connected` in NXOS. For example, `10.1.1.0/24(connected) & 10.1.1.1/32(local)`
- two devices: d1_nxos, d2_nxos
- two EBGP peering between them.
  - Both boxes do the `redist connected`.
  - BGP peering via `10.1.1.0/24`: `redist direct` only
    - observation:
      - `/32` routes will not be advertised, only `/24` will be advertise
      - `/24` will be in receiver's BGPRIB but not in MainRIB
    - route events:
      - d1_nxos BGPRIB: only `10.1.1.0/24` will be into BGPRIB and sends it to d2_nxos
      - d2_nxos BGPRIB: receives and put it into BGPRIB
      - MainRIB: do not put into MainRIB
  - BGP peering via `10.1.2.0/24`: `redist direct` + `/32` using `network` command
    - observation:
      - `/32` and `/24` both will be advertised
      - `/24` and `/24` will be in receiver's BGPRIB but not in MainRIB
    - route events:
      - d2_nxos BGPRIB: `10.1.2.0/24` & `10.1.2.2/32` both will be into BGPRIB and will be sent to d1_nxos
      - d1_nxos BGPRIB: receives it and put it into BGPRIB
      - MainRIB: do not put into MainRIB

## TLDR

- While using `redist direct route-map foo`, only `/24(connected)` will be imported and advertised. `/32(local)` will not be imported/advertised
  We can advertise `/32(local)` using network command.
- We can still advertise `/32(local)` using network command. In that case, `/24(connected)` and `/32(local)` route will be imported and advertised to peer but peer will not put it into MainRIB.
