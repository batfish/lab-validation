##LAB Facts

- Single VPC named `example`
- Three NLB
  - example-nlb-ip
    - NLB multiple AZ working scenario
  - example-target-az-different
    - Target and nlb in different AZ & Target AZ is not enabled on nlb. Hence, this nlb scenario will not work
  - nlb-eni-private-subnet
    - nlb is in private subnet & NGW is being used for internet traffic. This scenario will not work as return traffic will be blocked by NGW.

**Note:** `cross-zone` load balancing is enabled for all scenario
