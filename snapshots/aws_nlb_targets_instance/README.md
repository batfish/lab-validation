# Lab Facts

- This lab is created to understand the the `aws nlb` where the targets are `instance-id`.
- **Setup**
  - vpc `targets_instance`
    - two subnets; public and private
    - `nlb` is in `public` subnet and `target` in `private` subnet
    - Three `nlb to target` pair represents three different scenario below. `sg` is configured to control the traffic
      - `targets_instance_pri_pub_a1`: SG allows `nlb` private ip and `requester's` public ip address
      - `targets_instance_only_pub_a1`: SG allows only `requester's` public ip address
      - `targets_instance_only_pri_a`: SG allows only `nlb` private ip address
  - vpc `jump`
    - `jump` instance for management access
