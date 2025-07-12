# Lab Facts

- This lab is created to understand the the `aws nlb` where the targets are `ip`.
- **Setup**
  - vpc `targets_ip`
    - two subnets; public and private
    - `nlb` is in `public` subnet and `target` in `private` subnet
    - Four `nlb to target` pair represents four different scenario like below. `sg` is configured to control the traffic
      - instance `targets_ip_pd_pri_a`: proxy disable, SG allows `nlb` private ip
      - instance `targets_ip_pd_pub_a`: proxy disable, SG allows `requester's` public ip
      - instance `targets_ip_pe_pri_a`: proxy enable, SG allows `nlb` private ip
      - instance `targets_ip_pe_pub_a`: proxy enable, SG allows `requester's` public ip
  - vpc `jump`
    - `jump` instance for management access
