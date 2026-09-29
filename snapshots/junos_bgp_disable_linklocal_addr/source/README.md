# junos_bgp_disable_linklocal_addr

Tests where Junos accepts `disable-linklocal-addr` under `protocols bgp`
and what it changes in the IPv6 BGP UPDATEs a router sends. Juniper does
not document the statement, and `set protocols bgp ?` does not list it.

## Topology

sender (AS 65001) advertises one IPv6 prefix to receiver (AS 65002) on
each of four single-hop eBGP sessions, one per link. The sessions differ
only in where `disable-linklocal-addr` is configured on sender.

| Session | sender                    | receiver                  | `disable-linklocal-addr`   | Prefix              |
| ------- | ------------------------- | ------------------------- | -------------------------- | ------------------- |
| LINK12  | ge-0/0/0 `2001:db8:12::1` | ge-0/0/0 `2001:db8:12::2` | none                       | `2001:db8:100::/48` |
| LINK13  | ge-0/0/1 `2001:db8:13::1` | ge-0/0/1 `2001:db8:13::2` | group                      | `2001:db8:200::/48` |
| LINK14  | ge-0/0/2 `2001:db8:14::1` | ge-0/0/2 `2001:db8:14::2` | neighbor                   | `2001:db8:300::/48` |
| LINK15  | ge-0/0/3 `2001:db8:15::1` | ge-0/0/3 `2001:db8:15::2` | protocol, `PROTO` instance | `2001:db8:400::/48` |

Interface addresses are /64s. Link-local addresses are the Junos
defaults, derived from the containerlab interface MACs, so they change on
every deploy. The protocol-level statement is in the `PROTO`
virtual-router so it does not also apply to the master-instance
sessions.

receiver traces received UPDATEs with
`protocols bgp traceoptions file bgp-updates` and `flag update detail`.

## Results (vJunos-router 25.4R1.12)

### Hierarchy

The CLI completes `disable-linklocal-addr` as a leaf (`<[Enter]>`) under
`protocols bgp`, `protocols bgp group <g>`, and
`protocols bgp group <g> neighbor <n>`, although none of their `?`
listings include it.

| Configuration                                                             | Result         |
| ------------------------------------------------------------------------- | -------------- |
| `set protocols bgp disable-linklocal-addr`                                | accepted       |
| `set protocols bgp group <g> disable-linklocal-addr` (external group)     | accepted       |
| `set protocols bgp group <g> neighbor <n> disable-linklocal-addr`         | accepted       |
| group and neighbor level in a `type internal` group                       | accepted       |
| protocol, group, and neighbor level in a `virtual-router` instance        | accepted       |
| `set protocols bgp disable-linklocal-addr foo`                            | `syntax error` |
| `set protocols bgp family inet6 unicast disable-linklocal-addr`           | `syntax error` |
| `set protocols bgp group <g> family inet6 disable-linklocal-addr`         | `syntax error` |
| `set protocols bgp group <g> family inet6 unicast disable-linklocal-addr` | `syntax error` |
| `set routing-options disable-linklocal-addr`                              | `syntax error` |
| `set protocols bgp disable-link-local-addr`                               | `syntax error` |

Rejected forms fail when the `set` line is parsed; the accepted forms
pass `commit check`. `show bgp neighbor` and `show bgp group` show no
option or flag for the statement.

### Next hops

Without the statement, sender's MP_REACH_NLRI next hop is 32 bytes: the
global interface address followed by the interface's link-local address.
With the statement at any of the three levels, the next hop is 16 bytes
and contains only the global address. Set interactively, a group-level
statement on LINK13 or a neighbor-level statement on LINK12 left the
other session's next hop at 32 bytes; a protocol-level statement in the
master instance changed both.

| Session | MP_REACH next hop (receiver trace)            | Length |
| ------- | --------------------------------------------- | ------ |
| LINK12  | `2001:db8:12::1`, `fe80::aac1:abff:fedf:b0e2` | 32     |
| LINK13  | `2001:db8:13::1`                              | 16     |
| LINK14  | `2001:db8:14::1`                              | 16     |
| LINK15  | `2001:db8:15::1`                              | 16     |

`fe80::aac1:abff:fedf:b0e2` is sender's ge-0/0/0 link-local address.

The CLI views do not show the difference. On sender,
`show route advertising-protocol bgp <n> extensive` reports
`Nexthop: Self` for every session. On receiver,
`show route receive-protocol bgp <n> extensive` and
`show route <prefix> extensive` report the global address
(`Next hop: 2001:db8:1N::1 via ge-0/0/N.0`) for every session, including
LINK12.

Committing the statement on a live session neither resets the session
nor sends an UPDATE. The new encoding appears on the next UPDATE, here
triggered by `clear bgp neighbor <n> soft-inbound` on receiver. The
receiver's installed route keeps its next hop and age across the change.

### Batfish

Batfish reports each `disable-linklocal-addr` line as unrecognized
syntax. The lab tests pass because the receiver's routes use the global
next hop either way.

## Raw output

Captured from the running lab after the snapshot was collected.
Command lines start with `===== <node>>` (operational mode) or
`===== <node>#` (configuration mode). Device output is verbatim; `#`
lines in the tcpdump excerpt are labels.

receiver's trace (`show log bgp-updates`) after `clear log bgp-updates`
and `clear bgp neighbor <n> soft-inbound` for all four sessions, filtered
to the MP_REACH lines:

```
Sep 29 16:58:40.495435 BGP RECV 2001:db8:12::1+50437 -> 2001:db8:12::2+179
Sep 29 16:58:40.495870 BGP RECV flags 0x90 code MP_reach(14): length(44) AFI/SAFI 2/1
Sep 29 16:58:40.495879 BGP RECV 	nhop 2001:db8:12::1 len 16
Sep 29 16:58:40.495884 BGP RECV 	nhop fe80::aac1:abff:fedf:b0e2 len 16
Sep 29 16:58:40.495893 BGP RECV 	2001:db8:100::/48
Sep 29 16:58:40.496016 BGP RECV 2001:db8:13::1+57803 -> 2001:db8:13::2+179
Sep 29 16:58:40.496033 BGP RECV flags 0x90 code MP_reach(14): length(28) AFI/SAFI 2/1
Sep 29 16:58:40.496037 BGP RECV 	nhop 2001:db8:13::1 len 16
Sep 29 16:58:40.496041 BGP RECV 	2001:db8:200::/48
Sep 29 16:58:40.894396 BGP RECV 2001:db8:14::1+179 -> 2001:db8:14::2+55744
Sep 29 16:58:40.894443 BGP RECV flags 0x90 code MP_reach(14): length(28) AFI/SAFI 2/1
Sep 29 16:58:40.894454 BGP RECV 	nhop 2001:db8:14::1 len 16
Sep 29 16:58:40.894465 BGP RECV 	2001:db8:300::/48
Sep 29 16:58:40.895884 BGP RECV 2001:db8:15::1+54929 -> 2001:db8:15::2+179
Sep 29 16:58:40.895902 BGP RECV flags 0x90 code MP_reach(14): length(28) AFI/SAFI 2/1
Sep 29 16:58:40.895906 BGP RECV 	nhop 2001:db8:15::1 len 16
Sep 29 16:58:40.895911 BGP RECV 	2001:db8:400::/48
```

`tcpdump -nn -vvv` decode of the same UPDATEs, captured on receiver's
containerlab interfaces, filtered to the MP_REACH lines:

```
# receiver eth1 (ge-0/0/0)
	  Multi-Protocol Reach NLRI (14), length: 44, Flags [OE]:
	    nexthop: 2001:db8:12::1, fe80::aac1:abff:fedf:b0e2, nh-length: 32, no SNPA
# receiver eth2 (ge-0/0/1)
	  Multi-Protocol Reach NLRI (14), length: 28, Flags [OE]:
	    nexthop: 2001:db8:13::1, nh-length: 16, no SNPA
# receiver eth3 (ge-0/0/2)
	  Multi-Protocol Reach NLRI (14), length: 28, Flags [OE]:
	    nexthop: 2001:db8:14::1, nh-length: 16, no SNPA
# receiver eth4 (ge-0/0/3)
	  Multi-Protocol Reach NLRI (14), length: 28, Flags [OE]:
	    nexthop: 2001:db8:15::1, nh-length: 16, no SNPA
```

sender's advertisements on LINK12 (no statement) and LINK13
(group-level):

```
===== sender> show route advertising-protocol bgp 2001:db8:12::2 extensive

inet6.0: 13 destinations, 13 routes (13 active, 0 holddown, 0 hidden)
* 2001:db8:100::/48 (1 entry, 1 announced)
 BGP group LINK12 type External
     Nexthop: Self
     AS path: [65001] I

===== sender> show route advertising-protocol bgp 2001:db8:13::2 extensive

inet6.0: 13 destinations, 13 routes (13 active, 0 holddown, 0 hidden)
* 2001:db8:200::/48 (1 entry, 1 announced)
 BGP group LINK13 type External
     Nexthop: Self
     AS path: [65001] I
```

receiver's installed next hop for each prefix
(`show route <prefix> extensive`):

```
===== receiver> show route 2001:db8:100::/48 extensive
                Next hop: 2001:db8:12::1 via ge-0/0/0.0, selected
===== receiver> show route 2001:db8:200::/48 extensive
                Next hop: 2001:db8:13::1 via ge-0/0/1.0, selected
===== receiver> show route 2001:db8:300::/48 extensive
                Next hop: 2001:db8:14::1 via ge-0/0/2.0, selected
===== receiver> show route 2001:db8:400::/48 extensive
                Next hop: 2001:db8:15::1 via ge-0/0/3.0, selected
```

Adding the group-level statement to LINK12 on the live session, with
receiver's trace cleared first; sender's config was restored afterwards:

```
===== receiver> clear log bgp-updates
/var/log/bgp-updates cleared successfully

===== receiver> show route 2001:db8:100::/48 extensive | match "Age|Next hop:"
                Next hop: 2001:db8:12::1 via ge-0/0/0.0, selected
                Age: 7:14

===== sender# set protocols bgp group LINK12 disable-linklocal-addr

===== sender# commit
commit complete

===== receiver> show bgp neighbor 2001:db8:12::1 | match "Flaps|Last Event"
  Last State: OpenConfirm   Last Event: RecvKeepAlive
  Number of flaps: 0

===== receiver> show log bgp-updates | match "BGP RECV"

===== receiver> show route 2001:db8:100::/48 extensive | match "Age|Next hop:"
                Next hop: 2001:db8:12::1 via ge-0/0/0.0, selected
                Age: 7:40

===== receiver> clear bgp neighbor 2001:db8:12::1 soft-inbound

===== receiver> show log bgp-updates | match "BGP RECV"
Sep 29 17:00:02.335428 BGP RECV 2001:db8:12::1+50437 -> 2001:db8:12::2+179
Sep 29 17:00:02.335461 BGP RECV message type 2 (Update) length 68
Sep 29 17:00:02.336253 BGP RECV Update PDU length 68
Sep 29 17:00:02.336262 BGP RECV flags 0x40 code Origin(1): IGP, length(1)
Sep 29 17:00:02.336269 BGP RECV flags 0x40 code ASPath(2) (4-byte-cap) length 6: 65001
Sep 29 17:00:02.336273 BGP RECV flags 0x90 code MP_reach(14): length(28) AFI/SAFI 2/1
Sep 29 17:00:02.336282 BGP RECV 	nhop 2001:db8:12::1 len 16
Sep 29 17:00:02.336292 BGP RECV 	2001:db8:100::/48

===== receiver> show route 2001:db8:100::/48 extensive | match "Age|Next hop:"
                Next hop: 2001:db8:12::1 via ge-0/0/0.0, selected
                Age: 7:47
```

## Checks

`checks.yaml` verifies the four sessions and routes, runs the commit
checks in the table above on sender, and uses `bgp_update_next_hops` to
refresh each session and assert its traced next hops: global plus one
link-local for LINK12, global only for the others.
