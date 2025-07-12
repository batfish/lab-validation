# resolution_rib

This lab showcases the following resolution features of Juniper:

- static routes with `resolve`
- static routes with `no-resolve` (the default)
- `resolution rib <table> import`

There are two routers:

r1 <-> r2

- r1 is a JUNOS QFX router for which resolution behavior is under test.
  - A resolution rib import policy is configured allowing only routes with prefix-length 24.
  - From the right, it imports some iBGP routes and sets next hops on import in such a way as to showcase the impact of resolution policy.
  - Locally, it configures a bunch of static routes to cover the range of static route resolution behavior.
- r2 is an IOS router exporting its connected routes over iBGP.

The routes of interest on r1 and their expected activation behavior under the resolution policy follow:

## Static routes

- `10.10.0.0/32` -> `10.2.0.1`
  - Since 10.2.0.1 belongs to the connected network of an interface, the route should be installed regardless of resolution policy.
- `10.10.1.0/24` resolve -> `10.2.0.1`
  - Since 10.2.0.1 belongs to the connected network of an interface, the route should be installed regardless of resolution policy, even thought the `resolve` keyword is attached to this route.
- `10.10.2.0/24` -> `172.24.0.254`
  - Since 10.2.0.1 belongs to the connected network of an interface, the route should be installed regardless of resolution policy.
- `10.10.3.0/32` -> `10.10.2.1`
  - While the network matching the next hop meets the resolution policy, this route is not set to recursively resolve. So it should not be installed.
- `10.10.4.0/32` resolve -> `10.10.2.1`
  - This route is set to recursively resolve, and the routes visited during recursion all match the resolution policy. So the route should be installed.
- `10.10.5.0/32` resolve -> `10.10.1.1`
  - This route is set to recursively resolve, and the matching network for its next hop does meet the resolution policy. However, the route for the matching network's next hop does not match the resolution policy, so this route should not be installed.
- `10.10.6.0/32` -> `xe-0/0/4.0`
  - Since the next hop is an interface, it should always be installed as long as the interface is active.
- `10.10.7.0/32` resolve -> `10.10.6.0`
  - Although the next hop belongs to an interface route of sorts, testing shows that only connected routes may bypass the resolution policy. Since the matching route does not pass the policy, this route is not installed.
- `10.10.8.0/32` -> `discard`
  - Static discard routes are always installed
- `10.10.9.0/32` resolve -> `10.10.8.0`
  - The next hop belongs to a discard route. Testing shows that only connected routes may bypass the resolution policy. Since the matching route does not pass the policy, this route is not installed.

## BGP routes

The iBGP peering is done between physical interface addresses rather than loopbacks for simplicity.
There are 2 connected routes exported to r1 from r2 via iBGP:

- `10.100.0.0/24`
  - No rewriting of next-hop occurs. The next hop is therefore an IP on the peer interface, which is a connected route. Unlike static routes, resolution policy is _not_ skipped for connected next hops. The route is not installed.
- `10.100.1.0/24`
  - The next hop is rewritten to `172.24.0.254`. The matching route is `172.24.0.0/24`, which passes the resolution policy. This route is installed.
