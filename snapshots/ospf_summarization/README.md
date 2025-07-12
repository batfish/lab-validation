# ospf_summarization

This lab showcases OSPF area-range summarization on IOS and JUNOS.

There are three routers:

a01 <-> a02 <-> a2

- a01 is an IOS router in areas 0 and 1. It summarizes several networks from area 1, which are sent (except one) to area a02 via area 0.
- a02 is a JUNOS QFX router in areas 0 and 2. It similarly summarizes several networks from area 0, which are sent (except one) to its neighboring routers.
- a2 is an IOS router only in area 2. It receives summaries and other routes from a01 and a02 as inter-area routes.

Three types of summarization are performed on each of a01 and a02:

- default: send the summary with metric equal to the minimum(?) of contributing route costs, and suppress more specific routes
- no-advertise/restrict: suppress the summary AND more specific routes (but still install a summary null route locally)
- cost/override-metric: like default, but send the summary with a fixed cost instead of a dynamic one computed from contributing route costs
