# LAB Facts

- This lab is created to test/understand bgp behavior configured using `local-as` command.
- Two devices, `ios1` `nxos1`. Both are configured with `local-as`
- ios1
  - global as 65500
  - local-as 65501
  - remote-as 65502
- nxos1
  - global as 65600
  - local-as 65502
  - remote-as 65501
- bgp peer will receive prefix with as-path prepended like (local-as, remote-as, remote-peer global as). For example, `nxos1` will receive (65502 65501 65500)
