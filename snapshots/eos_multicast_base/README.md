Lab details can be found here - [Basic MPLS/VPNv4 Lab](https://docs.google.com/document/d/1iaF-yDEVlCtnD4UXBKE8trfTTMaTP2LX7s1TxCt1faI/edit)

The lab consists of 3 devices of interest with a number of devices/endpoints providing the necessary hooks to enable creation of multicast state.

The core devices are rp1, rp2 and rcvr. They are all EOS devices.

The lab focuses on PIM SSM operation with static RPs plus IGMP version 3.

fake_rcvr1 and fake_rcvr2 are Cisco IOS devices that act like hosts joining specific multicast groups. These devices are part of the test harness and are the means by which IGMP joins for the relevant groups are injecteded into the topoogy. They are not part of the devices under test and as such do not need to be validated. In the future, if there is a simple mechanism to inject multicast state via a traffic generator, they can be replaced.

src1 and src2 are GNS3 virtual PCs and are the simulated multicast sources. They DO NOT generate multicast traffic. They are present so that the appropriate interfaces on rp1 and rp2 would be up.
