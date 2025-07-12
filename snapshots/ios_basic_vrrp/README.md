### LAB Facts:

1. Lab is on a very basic configuration Virtual Router Redundancy Protocol (VRRP) for High Availibility.
2. There are 4 Devices BR1, BR2, LAN-RTR & WAN-RTR
3. BR1 & BR2 have a static route pointing towards WAN-RTR
4. BR1 is explicitly configured as ACTIVE Gateway, with priority 110 (group no.12). And Preempt is enabled to re-elect BR1 and ACTIVE in case of it reboots.
5. BR2 is the STANDBY router. In case of BR1 fails, BR2 becomes Active Gateway.
6. The GW vIP is : 192.168.1.254
7. LAN-RTR is configured with a static route pointing towards GW IP: 192.168.1.254
8. WAN- RTR is configured with 2 static routes for the reverse path.
9. LAN-RTR always prefers BR1 as the GW to reach WAN-RTR network 192.168.2.1/24
