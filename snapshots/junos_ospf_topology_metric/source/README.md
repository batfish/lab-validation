# junos_ospf_topology_metric

Tests whether Junos accepts `topology default metric <n>` at the OSPF and
OSPF3 process level (for example
`set protocols ospf topology default metric 65450`), in the master
instance and in a virtual-router. Juniper documents `topology <name>
metric` only under `protocols ospf area <a> interface <i>`, which this lab
uses as a positive control.

## Topology

dut (vJunos-router) runs OSPF and OSPF3 area 0 with peer (cEOS) on three
point-to-point links.

| Link | dut        | peer      | IPv4          | IPv6              | dut instance          |
| ---- | ---------- | --------- | ------------- | ----------------- | --------------------- |
| 1    | ge-0/0/0.0 | Ethernet1 | `10.0.1.0/31` | `2001:db8:1::/64` | master                |
| 2    | ge-0/0/1.0 | Ethernet2 | `10.0.2.0/31` | `2001:db8:2::/64` | master                |
| 3    | ge-0/0/2.0 | Ethernet3 | `10.0.3.0/31` | `2001:db8:3::/64` | `VR` (virtual-router) |

dut's loopbacks are `10.255.0.1`/`2001:db8:ff::1` (lo0.0, master) and
`10.255.1.1`/`2001:db8:ff:1::1` (lo0.1, `VR`); peer's are `.2`/`::2` on
the same prefixes, with a cost of 10. All interface costs default to 1.

`configs/dut.cfg` is the collected state: interface-level
`topology default metric 100` (OSPF) and `metric 100` (OSPF3) on
ge-0/0/0.0 and ge-0/0/2.0, plus the process-level `topology default;`
that `load set` keeps from the rejected line. The tests below started
from the same configuration without those six statements; every change
was rolled back afterward, and `show system rollback 6 compare 0`
against the startup commit was empty.

## Results (vJunos-router 25.4R1.12)

`show version`: `Model: vmx`, `Junos: 25.4R1.12`.

### Syntax

| Configuration                                                                | Result                       |
| ---------------------------------------------------------------------------- | ---------------------------- |
| `set protocols ospf topology default metric 65450`                           | `syntax error` at `metric`   |
| `set routing-instances VR protocols ospf topology default metric 65450`      | `syntax error` at `metric`   |
| `set protocols ospf3 topology default metric 65450`                          | `syntax error` at `topology` |
| `set routing-instances VR protocols ospf3 topology default metric 65450`     | `syntax error` at `topology` |
| `set protocols ospf topology default metric N`, N = 0, 1, 65535, 65536       | `syntax error` at `metric`   |
| `set protocols ospf topology ipv4-multicast metric 65450`                    | `syntax error` at `metric`   |
| `set protocols ospf topology <undefined-name> metric 65450`                  | `syntax error` at `metric`   |
| `set protocols ospf topology default`                                        | accepted                     |
| `set protocols ospf area 0.0.0.0 interface <i> topology default metric 100`  | accepted (also in `VR`)      |
| `set protocols ospf3 area 0.0.0.0 interface <i> topology default metric 100` | `syntax error` at `topology` |
| `set protocols ospf3 area 0.0.0.0 interface <i> metric 100`                  | accepted (also in `VR`)      |

The process-level `topology default` stanza exists (for multi-topology
OSPF) but has no `metric` child. Its `?` listing is `backup-spf-options`,
`overload`, `prefix-export-limit`, `rib-group`, and `spf-options`; the
interface-level `topology default ?` lists `metric` (`1..65535`) and
`bandwidth-based-metrics`. OSPF3 has no `topology` statement at the
process or interface level.

The rejection does not depend on how the line is entered. Interactive
`set`, `load set terminal`, and `load merge terminal` (bracketed form) all
report a syntax error at the same token. The two load commands still
print `load complete` and keep the valid prefix: for OSPF, the candidate
then contains `topology default;` and `commit check` succeeds. For OSPF3,
nothing is loaded.

The rejected statement never reaches the candidate configuration, so it
cannot appear in `show configuration` or `| display set` output.

### Operational effect

The process-level statement cannot be committed, so it has no
operational effect. Committing what `load set` keeps
(`topology default;` in the master and `VR` OSPF instances) changed
nothing: interface costs, routes, and router LSAs were identical, and
dut's four router LSAs kept their sequence numbers and checksums.

The interface-level control changed costs as documented:

| Observation (dut)                                    | Baseline             | Control (metric 100 on ge-0/0/0.0, ge-0/0/2.0) |
| ---------------------------------------------------- | -------------------- | ---------------------------------------------- |
| `show ospf interface detail` ge-0/0/0.0, ge-0/0/2.0  | `Cost: 1`            | `Topology default (ID 0) -> Cost: 100`         |
| `show ospf3 interface detail` ge-0/0/0.0, ge-0/0/2.0 | `Cost 1`             | `Cost 100`                                     |
| OSPF router LSA, link 1 and link 3 (also on peer)    | metric 1             | metric 100                                     |
| `10.255.0.2/32`, `2001:db8:ff::2/128`                | metric 11, links 1+2 | metric 11, link 2 only                         |
| `10.255.1.2/32`, `2001:db8:ff:1::2/128` (`VR`)       | metric 11            | metric 110                                     |

### Batfish

Batfish reports `set protocols ospf topology default` and
`set routing-instances VR protocols ospf topology default` as
unrecognized syntax. The lab tests pass; Batfish computes the IPv4 OSPF
routes above, including the interface-level metric of 100.

## Raw output

Captured from the running lab. Command lines start with `===== dut>`
(operational mode) or `===== dut#` (configuration mode). Blocks are
excerpts; device lines are verbatim apart from trailing whitespace. With
interactive `set`, the CLI redisplays the line when it detects the
error, so the input appears twice.

Interactive `set`, process level, master and `VR`:

```
===== dut# set protocols ospf topology default metric 65450
set protocols ospf topology default metric
                                               ^
syntax error.

admin@dut# set protocols ospf topology default metric   65450
                                               ^
syntax error.

[edit]
===== dut# show | compare

[edit]
===== dut# commit check
configuration check succeeds

[edit]
===== dut# set routing-instances VR protocols ospf topology default metric 65450
set routing-instances VR protocols ospf topology default metric
                                                                    ^
syntax error.

admin@dut# set routing-instances VR protocols ospf topology default metric   65450
                                                                    ^
syntax error.
```

`load set terminal` and `load merge terminal`:

```
admin@dut# load set terminal
[Type ^D at a new line to end input]
set protocols ospf topology default metric 65450
^Dterminal:1:(36) syntax error: metric
load complete

[edit]
admin@dut# show | compare
[edit protocols ospf]
+    topology default;

[edit]
admin@dut# commit check
configuration check succeeds

[edit]
admin@dut# rollback 0
load complete

[edit]
admin@dut# load set terminal
[Type ^D at a new line to end input]
set protocols ospf3 topology default metric 65450
^Dterminal:1:(20) syntax error: topology
load complete

[edit]
admin@dut# show | compare

[edit]
admin@dut# load set terminal
[Type ^D at a new line to end input]
set routing-instances VR protocols ospf topology default metric 65450
^Dterminal:1:(57) syntax error: metric
load complete

[edit]
admin@dut# show | compare
[edit routing-instances VR protocols ospf]
+      topology default;

[edit]
admin@dut# load set terminal
[Type ^D at a new line to end input]
set routing-instances VR protocols ospf3 topology default metric 65450
^Dterminal:1:(41) syntax error: topology
load complete

[edit]
admin@dut# show | compare

[edit]
admin@dut# load merge terminal
[Type ^D at a new line to end input]
protocols {
    ospf {
        topology default {
            metric 65450;
        }
    }
}
^Dterminal:4:(18) syntax error: metric
  [edit protocols ospf topology default]
    'metric 65450;'
      syntax error
load complete (1 errors)

[edit]
admin@dut# show | compare
[edit protocols ospf]
+    topology default;

[edit]
admin@dut# load merge terminal
[Type ^D at a new line to end input]
protocols {
    ospf3 {
        topology default {
            metric 65450;
        }
    }
}
^Dterminal:3:(16) syntax error: topology
  [edit protocols ospf3]
    'topology default {'
      syntax error
terminal:5:(9) error recovery ignores input until this point: }
  [edit protocols ospf3]
    '}'
      error recovery ignores input until this point
[edit protocols]
  'ospf3'
    warning: statement has no contents; ignored
load complete (2 errors)

[edit]
admin@dut# show | compare

[edit]
admin@dut# load set terminal
[Type ^D at a new line to end input]
set protocols ospf area 0.0.0.0 interface ge-0/0/0.0 topology default metric 100
^Dload complete

[edit]
admin@dut# show | compare
[edit protocols ospf area 0.0.0.0 interface ge-0/0/0.0]
+      topology default metric 100;

[edit]
admin@dut# commit check
configuration check succeeds
```

CLI help:

```
admin@dut# set protocols ospf topology default ?
Possible completions:
  <[Enter]>            Execute this command
+ apply-groups         Groups from which to inherit configuration data
+ apply-groups-except  Don't inherit configuration data from these groups
> backup-spf-options   Configure options for backup SPF
  overload             Set the overload mode (repel transit traffic)
  prefix-export-limit  Maximum number of prefixes that can be exported (0..4294967295)
  rib-group            Routing table group for importing routes
> spf-options          Configure options for SPF
  |                    Pipe through a command

admin@dut# set protocols ospf area 0.0.0.0 interface ge-0/0/0.0 topology default ?
Possible completions:
  <[Enter]>            Execute this command
+ apply-groups         Groups from which to inherit configuration data
+ apply-groups-except  Don't inherit configuration data from these groups
> bandwidth-based-metrics  Configure bandwidth based metrics
  metric               Topology metric (1..65535)
  |                    Pipe through a command
```

`set protocols ospf ?` lists `> topology  Topology parameters`;
`set protocols ospf3 ?` and
`set protocols ospf3 area 0.0.0.0 interface ge-0/0/0.0 ?` do not list
`topology`.

Committed process-level `topology default`, normalized:

```
===== dut# show | compare
[edit routing-instances VR protocols ospf]
+      topology default;
[edit protocols ospf]
+    topology default;

[edit]
===== dut# commit check
configuration check succeeds

[edit]
===== dut# commit comment "process-level topology default"
commit complete

[edit]
===== dut# exit configuration-mode
Exiting configuration mode
===== dut> show configuration protocols ospf
topology default;
area 0.0.0.0 {
    interface ge-0/0/0.0 {
        interface-type p2p;
    }
    interface ge-0/0/1.0 {
        interface-type p2p;
    }
    interface lo0.0 {
        passive;
    }
}
===== dut> show configuration protocols ospf | display set
set protocols ospf topology default
set protocols ospf area 0.0.0.0 interface ge-0/0/0.0 interface-type p2p
set protocols ospf area 0.0.0.0 interface ge-0/0/1.0 interface-type p2p
set protocols ospf area 0.0.0.0 interface lo0.0 passive
===== dut> show configuration routing-instances VR protocols ospf | display set
set routing-instances VR protocols ospf topology default
set routing-instances VR protocols ospf area 0.0.0.0 interface ge-0/0/2.0 interface-type p2p
set routing-instances VR protocols ospf area 0.0.0.0 interface lo0.1 passive
```

dut's router LSAs (OSPF master, OSPF3 master, OSPF `VR`, OSPF3 `VR`)
before and about 7 minutes after that commit (only Age differs):

```
Router  *10.255.0.1       10.255.0.1       0x80000004    86  0x22 0x9fea  84
Router     *0.0.0.0          10.255.0.1       0x80000002    78  0x724f  56
Router  *10.255.1.1       10.255.1.1       0x80000003    91  0x22 0x5274  60
Router     *0.0.0.0          10.255.1.1       0x80000001    85  0xbd6   40

Router  *10.255.0.1       10.255.0.1       0x80000004   497  0x22 0x9fea  84
Router     *0.0.0.0          10.255.0.1       0x80000002   489  0x724f  56
Router  *10.255.1.1       10.255.1.1       0x80000003   502  0x22 0x5274  60
Router     *0.0.0.0          10.255.1.1       0x80000001   496  0xbd6   40
```

Interface-level control, collected state:

```
===== dut> show ospf database router advertising-router 10.255.0.1 extensive

    OSPF database, Area 0.0.0.0
 Type       ID               Adv Rtr           Seq      Age  Opt  Cksum  Len
Router  *10.255.0.1       10.255.0.1       0x80000007   126  0x22 0x3c84  84
  bits 0x0, link count 5
  id 10.255.0.2, data 10.0.1.0, Type PointToPoint (1)
    Topology count: 0, Default metric: 100
  id 10.0.1.0, data 255.255.255.254, Type Stub (3)
    Topology count: 0, Default metric: 100
  id 10.255.0.2, data 10.0.2.0, Type PointToPoint (1)
    Topology count: 0, Default metric: 1
  id 10.0.2.0, data 255.255.255.254, Type Stub (3)
    Topology count: 0, Default metric: 1
  id 10.255.0.1, data 255.255.255.255, Type Stub (3)
    Topology count: 0, Default metric: 0
===== dut> show route 10.255.0.2/32 exact

10.255.0.2/32      *[OSPF/10] 00:02:06, metric 11
                    >  to 10.0.2.1 via ge-0/0/1.0
===== dut> show route 2001:db8:ff::2/128 exact

2001:db8:ff::2/128 *[OSPF3/10] 00:02:06, metric 11
                    >  to fe80::a8c1:abff:fef6:8676 via ge-0/0/1.0
===== dut> show route 10.255.1.2/32 exact table VR.inet.0

10.255.1.2/32      *[OSPF/10] 00:02:07, metric 110
                    >  to 10.0.3.1 via ge-0/0/2.0
===== dut> show route 2001:db8:ff:1::2/128 exact table VR.inet6.0

2001:db8:ff:1::2/128
                   *[OSPF3/10] 00:02:07, metric 110
                    >  to fe80::a8c1:abff:fe22:eb09 via ge-0/0/2.0
```

Baseline routes (no metric statements):

```
10.255.0.2/32      *[OSPF/10] 00:01:26, metric 11
                    >  to 10.0.1.1 via ge-0/0/0.0
                       to 10.0.2.1 via ge-0/0/1.0
2001:db8:ff::2/128 *[OSPF3/10] 00:01:10, metric 11
                       to fe80::a8c1:abff:fe50:d2b4 via ge-0/0/0.0
                    >  to fe80::a8c1:abff:fef6:8676 via ge-0/0/1.0
10.255.1.2/32      *[OSPF/10] 00:01:31, metric 11
                    >  to 10.0.3.1 via ge-0/0/2.0
2001:db8:ff:1::2/128
                   *[OSPF3/10] 00:01:15, metric 11
                    >  to fe80::a8c1:abff:fe22:eb09 via ge-0/0/2.0
```

Restore check after the last rollback (empty diff against the startup
commit):

```
===== dut> show system rollback 6 compare 0
```
