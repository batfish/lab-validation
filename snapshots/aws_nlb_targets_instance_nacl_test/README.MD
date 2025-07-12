##LAB Facts
This lab is created to test/understand packet journey between NLB and target where targets are configured with id.
It is configured in a way where we will try to make sure that behavior aligns with AWS by blocking packet in & out using NACL.

####**AWS NLB Targets with id follow below rules**

- original customer source ip will be preserved
- dest ip will be changed to target IP before sending packet to target

Assuming above facts, lab is configured to deny packet at each hop when user initiate traffic from internet

- tip_nno - target_ip nlb_nacl_out
  - nlb subnet nacl denies packet going out by blocking target private ip
  - NLB - 10.2.1.16, 184.72.231.233
  - target - 10.2.101.100
- cip_tni - customer_ip target_NACL_in
  - target subnet nacl denies packet coming in by blocking customer original ip(8.8.8.8/67.160.71.197)
  - NLB - 10.2.2.143, 35.153.244.97
  - target - 10.2.102.100
- cip_tno - custoerm_ip target NACL_out
  - target subnet nacl denies packet going out by blocking customer original ip(8.8.8.8/67.160.71.197)
  - NLB - 10.2.3.134, 52.7.224.35
  - target - 10.2.103.100
- tip_nni - target_ip nlb_nacl_in
  - nlb subnet nacl denies packet coming in by blocking target private ip
  - NLB - 10.2.4.228, 34.195.4.88
  - target - 10.2.104.100

**Note:**

- NLB in this lab is only configured the HTTP service. Other applications are being filtered out.
- These keywords like `tip, cip` are attached to appropriate nlb,instance,nacl

####**Opposite scenario:**
we also have one opposite scenario unlike above where we are trying to block packet based on NLB private ip address but it should not be blocked as NLB preservers original source ip address.

- nip_tni - nlb_ip target_nacl_in
  - Trying to block nlb private ip on target nacl but it does not block because NACL filters based on original ip address
  - NLB - 10.2.5.156, 54.205.251.252
  - target - 10.2.105.100
