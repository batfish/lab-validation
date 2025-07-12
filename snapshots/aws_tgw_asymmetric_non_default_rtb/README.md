# Lab Facts

- This lab is created to test asymmetric traffic behavior in `multi tgw` environment.
- vpc `bat` forwards the traffic to `tgw-bat` to reach to vpc `fish`
- vpc `fish` forwards the traffic to `tgw-fish` to reach to vpc `bat`
- Forward and return traffic will traverse via different `tgw`
- **Setup**
  - vpc `bat`
    - tgw `tgw-bat`
  - vpc `fish`
    - tgw `tgw-fish`
