A simple 2-node network showcasing OSPF unnumbered on Cumulus FRR.

r1 <=> r2

r1 and r2 connect to each other on their respective `swp1` interfaces.

r1 has a loopback interface with a /32 IP address, which is also assigned to its swp1 interface. The same is true of r2.
The swp1 interface is configured to use point-to-point mode for OSPF.

An OSPF session is established, and each router has routes to the neighbor's advertised networks via the neighbor's loopback IP, for which there is a special OSPF interface route installed.
