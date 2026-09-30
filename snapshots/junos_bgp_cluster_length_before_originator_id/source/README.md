# junos_bgp_cluster_length_before_originator_id

Tests where Junos accepts `protocols bgp path-selection
compare-cluster-length-before-originator-id` and how it changes BGP
route selection. `set protocols bgp path-selection ?` does not list the
statement, and the
[`path-selection` reference](https://www.juniper.net/documentation/us/en/software/junos/cli-reference/topics/ref/statement/path-selection-edit-protocols-bgp.html)
does not document it.

## Topology

All six nodes are iBGP speakers in AS 65000. origa and origb both
originate 203.0.113.0/24 (a Null0 static and `network`), and route
reflectors carry the two copies to dut:

```
origa -- rra ------------ dut (master: ge-0/0/1, KNOB: ge-0/0/3)    path A
origb -- rrb2 -- rrb1 --- dut (master: ge-0/0/0, KNOB: ge-0/0/2)    path B
```

| Path | Originator ID      | Cluster list            | dut peer (master / KNOB) | Peer router ID    |
| ---- | ------------------ | ----------------------- | ------------------------ | ----------------- |
| A    | 10.255.0.9 (origa) | `10.255.1.2`            | 10.0.2.1 / 10.0.12.1     | 10.255.0.2 (rra)  |
| B    | 10.255.0.1 (origb) | `10.255.1.3 10.255.1.4` | 10.0.1.1 / 10.0.11.1     | 10.255.0.3 (rrb1) |

rra (cluster 10.255.1.2) reflects origa's route. rrb2 (cluster
10.255.1.4) reflects origb's route to rrb1, whose client it is, and
rrb1 (cluster 10.255.1.3) reflects it again. Every reflector sets
next-hop-self toward the next router, so both paths reach dut with a
directly connected next hop (Metric2 0). The two paths have the same
local preference, AS path (empty), origin, and MED (none), so they tie
until the originator-ID and cluster-list-length steps. The two steps
prefer opposite paths: B has the lower originator ID, A has the shorter
cluster list.

dut peers with rra and rrb1 twice. The master instance has no
`path-selection` statement. The `KNOB` virtual-router has its own pair of
sessions, over ge-0/0/2 and ge-0/0/3, with the statement configured.
The snapshot therefore captures both behaviors at once.

Path B also has the lower peer address in both instances (10.0.1.1 <
10.0.2.1, 10.0.11.1 < 10.0.12.1), so when A wins, the final
peer-address tie-break did not decide it. Path A's peer has the lower
router ID (10.255.0.2 < 10.255.0.3), so when B wins on "Router ID", the
compared values were the originator IDs.

Only dut runs Junos. The other five nodes are cEOS 4.36.0.1F. They
only originate and reflect, and six vJunos-router VMs oversubscribed
the 16-vCPU lab host: each uses about 2.5 cores at idle.

## Results (vJunos-router 25.4R1.12)

### Hierarchy

`set protocols bgp path-selection ?` does not list the statement, but
`set protocols bgp path-selection compare-cluster-length-before-originator-id ?`
offers `<[Enter]>`, so it is a leaf that takes no argument.

| Configuration                                                                      | Result         |
| ---------------------------------------------------------------------------------- | -------------- |
| `set protocols bgp path-selection compare-cluster-length-before-originator-id`     | accepted       |
| `set routing-instances <vr> protocols bgp path-selection ...` (`virtual-router`)   | accepted       |
| `set routing-instances <v> protocols bgp path-selection ...` (`vrf`)               | accepted       |
| `set logical-systems <ls> protocols bgp path-selection ...`                        | accepted       |
| with `always-compare-med` and `external-router-id`                                 | accepted       |
| with `cisco-non-deterministic`                                                     | accepted       |
| `set protocols bgp group <g> path-selection ...`                                   | `syntax error` |
| `set protocols bgp group <g> neighbor <n> path-selection ...`                      | `syntax error` |
| `set routing-instances <vr> protocols bgp group <g> path-selection ...`            | `syntax error` |
| `set protocols bgp family inet unicast path-selection ...`                         | `syntax error` |
| `set protocols bgp compare-cluster-length-before-originator-id`                    | `syntax error` |
| `set protocols bgp group <g> compare-cluster-length-before-originator-id`          | `syntax error` |
| `set routing-options compare-cluster-length-before-originator-id`                  | `syntax error` |
| `set protocols bgp path-selection compare-cluster-length-before-originator-id foo` | `syntax error` |

`path-selection` itself does not exist at the group or neighbor level,
so the statement is per-instance only. Rejected forms fail when the
`set` line is parsed; accepted forms pass `commit check`.

### Route selection

| dut table     | Statement | Active path | Inactive path's reason                        |
| ------------- | --------- | ----------- | --------------------------------------------- |
| `inet.0`      | no        | B           | `Not Best in its group - Router ID`           |
| `KNOB.inet.0` | yes       | A           | `Not Best in its group - Cluster list length` |

Without the statement, Junos compares originator IDs before
cluster-list length and selects B. With it, Junos compares cluster-list
length first and selects A.

Toggling the statement in the master instance on the running lab moves
`inet.0` from B to A on commit and back to B when it is deleted. Neither
commit resets a session, and no route refresh is needed.

### Batfish

Batfish reports the statement as unrecognized syntax and selects path B
in both instances, which matches the device only in the master instance.
`test_bgp_rib_routes[dut]` is sickbayed to
batfish/batfish#10370.

Two lab-validation behaviors affect how this shows up:

- `JunosValidator.validate_bgp_rib_routes` drops every Batfish iBGP route
  in a non-default VRF (intended for EVPN-leaked routes). Batfish's
  `KNOB` route is removed before matching, so the test reports the
  device's `KNOB` route as having no match instead of reporting a
  next-hop mismatch (batfish/lab-validation#239).
- The Junos main-RIB comparison ignores next-hop IPs on BGP routes, so
  `test_main_rib_routes[dut]` passes even though the `KNOB` next hops
  differ (device 10.0.12.1, Batfish 10.0.11.1).

## Limitations

- One Junos release and platform: vJunos-router 25.4R1.12 (`Model:
vmx`).
- The reflectors and originators are cEOS, not Junos. The experiment
  only depends on the attributes dut receives, which are shown below.
- Each instance has exactly two candidate paths. The lab does not test
  paths with equal cluster-list lengths, paths without an ORIGINATOR_ID
  (where Junos compares the peer's router ID), or interactions with
  `cisco-non-deterministic` or `external-router-id` beyond commit.
- Both paths carry origin incomplete (`?`), from the EOS `network`
  statement for a static route.

## Raw output

Captured from the running lab after the snapshot was collected.
Command lines start with `===== <node>>` (operational mode) or
`===== <node>#` (configuration mode). Device output is verbatim except
that the CLI's trailing `[edit]` and prompt lines are omitted.

Version and the attributes dut receives in the master instance (the
`KNOB` sessions carry the same attributes):

```
===== dut> show version | match "Model|Junos:"
Model: vmx
Junos: 25.4R1.12

===== dut> show route receive-protocol bgp 10.0.1.1 extensive | except mgmt_junos

inet.0: 6 destinations, 7 routes (6 active, 0 holddown, 0 hidden)
* 203.0.113.0/24 (2 entries, 1 announced)
     Accepted
     Nexthop: 10.0.1.1
     Localpref: 100
     AS path: ?  (Originator)
     Cluster list:  10.255.1.3 10.255.1.4
     Originator ID: 10.255.0.1


KNOB.inet.0: 5 destinations, 6 routes (5 active, 0 holddown, 0 hidden)

===== dut> show route receive-protocol bgp 10.0.2.1 extensive | except mgmt_junos

inet.0: 6 destinations, 7 routes (6 active, 0 holddown, 0 hidden)
  203.0.113.0/24 (2 entries, 1 announced)
     Accepted
     Nexthop: 10.0.2.1
     Localpref: 100
     AS path: ?  (Originator)
     Cluster list:  10.255.1.2
     Originator ID: 10.255.0.9


KNOB.inet.0: 5 destinations, 6 routes (5 active, 0 holddown, 0 hidden)
```

Selected paths, `inet.0` (no statement) then `KNOB.inet.0` (statement):

```
===== dut> show route 203.0.113.0/24 detail | match "Source:|State:|Inactive reason|Cluster list|Originator ID|Router ID|Metric2|Localpref|AS path"
                Source: 10.0.1.1
                State: <Active Int Ext>
                Age: 6:29 	Metric2: 0
                Validation State: unverified
                AS path: ?  (Originator)
                Cluster list:  10.255.1.3 10.255.1.4
                Originator ID: 10.255.0.1
                Localpref: 100
                Router ID: 10.255.0.3
                Source: 10.0.2.1
                State: <NotBest Int Ext Changed>
                Inactive reason: Not Best in its group - Router ID
                Age: 6:25 	Metric2: 0
                Validation State: unverified
                AS path: ?  (Originator)
                Cluster list:  10.255.1.2
                Originator ID: 10.255.0.9
                Localpref: 100
                Router ID: 10.255.0.2
                Source: 10.0.12.1
                State: <Active Int Ext>
                Age: 6:16 	Metric2: 0
                Validation State: unverified
                AS path: ?  (Originator)
                Cluster list:  10.255.1.2
                Originator ID: 10.255.0.9
                Localpref: 100
                Router ID: 10.255.0.2
                Source: 10.0.11.1
                State: <NotBest Int Ext>
                Inactive reason: Not Best in its group - Cluster list length
                Age: 6:20 	Metric2: 0
                Validation State: unverified
                AS path: ?  (Originator)
                Cluster list:  10.255.1.3 10.255.1.4
                Originator ID: 10.255.0.1
                Localpref: 100
                Router ID: 10.255.0.3
```

Toggling the statement in the master instance:

```
===== dut> show route table inet.0 203.0.113.0/24 detail | match "Source:|Inactive reason"
                Source: 10.0.1.1
                Source: 10.0.2.1
                Inactive reason: Not Best in its group - Router ID

===== dut# set protocols bgp path-selection compare-cluster-length-before-originator-id

===== dut# commit
commit complete

===== dut> show route table inet.0 203.0.113.0/24 detail | match "Source:|Inactive reason"
                Source: 10.0.2.1
                Source: 10.0.1.1
                Inactive reason: Not Best in its group - Cluster list length

===== dut> show bgp neighbor 10.0.1.1 | match Flaps
  Number of flaps: 0

===== dut> show bgp neighbor 10.0.2.1 | match Flaps
  Number of flaps: 0

===== dut# delete protocols bgp path-selection compare-cluster-length-before-originator-id

===== dut# commit
commit complete

===== dut> show route table inet.0 203.0.113.0/24 detail | match "Source:|Inactive reason"
                Source: 10.0.1.1
                Source: 10.0.2.1
                Inactive reason: Not Best in its group - Router ID
```

CLI completion:

```
===== dut# set protocols bgp path-selection ?
Possible completions:
  always-compare-med   Always compare MED values, regardless of neighbor AS
+ apply-groups         Groups from which to inherit configuration data
+ apply-groups-except  Don't inherit configuration data from these groups
  as-path-ignore       Ignore AS path comparison during path selection
  cisco-non-deterministic  Use Cisco IOS nondeterministic path selection algorithm
  external-router-id   Compare router ID on BGP externals
  l2vpn-use-bgp-rules  Use standard BGP rules during L2VPN path selection
> med-plus-igp         Add IGP cost to next-hop to MED before comparing MED values

===== dut# set protocols bgp path-selection compare-cluster-length-before-originator-id ?
Possible completions:
  <[Enter]>            Execute this command
  always-compare-med   Always compare MED values, regardless of neighbor AS
+ apply-groups         Groups from which to inherit configuration data
+ apply-groups-except  Don't inherit configuration data from these groups
  as-path-ignore       Ignore AS path comparison during path selection
  cisco-non-deterministic  Use Cisco IOS nondeterministic path selection algorithm
  external-router-id   Compare router ID on BGP externals
  l2vpn-use-bgp-rules  Use standard BGP rules during L2VPN path selection
> med-plus-igp         Add IGP cost to next-hop to MED before comparing MED values
  |                    Pipe through a command
```

## Checks

`checks.yaml` verifies the seven BGP sessions, uses `bgp_active_path` to
assert the selected path and the other path's inactive reason in each
dut table, and runs the commit checks in the hierarchy table on dut.
