##Lab facts

- Single web server(sitting in private subnet) is secured by panos FW
- Web server forwards the traffic to FW, FW do the appropriate NAT and forward traffic to/from internet
- Setup
  - VPC
    - Subnets
      - public
        - devices
          -fw
      - private
        - devices
          - web server
          - fw
- Panos fw having three interfaces
  - outside - public subnet
  - mgmt - public subnet
  - inside - private subnet
