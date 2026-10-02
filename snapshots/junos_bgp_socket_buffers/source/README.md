# junos_bgp_socket_buffers

Tests where Junos accepts `receive-buffer` and `send-buffer` under
`protocols bgp`, which values they take, and how Junos displays them.
Juniper does not document the statements, and `set protocols bgp ?` does
not list them.

## Topology

dut (vJunos-router, AS 65001) has two eBGP sessions to peer (cEOS,
AS 65002). peer advertises 203.0.113.0/24 on both.

| Session | dut instance           | dut                        | peer                     |
| ------- | ---------------------- | -------------------------- | ------------------------ |
| master  | master                 | ge-0/0/0 `192.0.2.0/31`    | Ethernet1 `192.0.2.1`    |
| VR1     | VR1 (`virtual-router`) | ge-0/0/1 `198.51.100.0/31` | Ethernet2 `198.51.100.1` |

Each instance configures both statements at all three levels: 64k at
the protocol level, 128k in group TEST, and 256k on the neighbor. The
master instance uses the statements as written below; VR1 spells the
same sizes as `65536`, `128K`, and `0x40000`.

```
set protocols bgp receive-buffer 64k
set protocols bgp send-buffer 64k
set protocols bgp group TEST receive-buffer 128k
set protocols bgp group TEST send-buffer 128k
set protocols bgp group TEST neighbor 192.0.2.1 receive-buffer 256k
set protocols bgp group TEST neighbor 192.0.2.1 send-buffer 256k
```

## Results (vJunos-router 25.4R1.12, model vmx)

### Hierarchy

`?` after either keyword prints `No valid completions`; after a value it
offers `<[Enter]>`. `display xml` wraps each statement in
`<undocumented>`.

| Configuration                                                      | Result         |
| ------------------------------------------------------------------ | -------------- |
| `protocols bgp`, `group <g>`, `group <g> neighbor <n>` (external)  | accepted       |
| group and neighbor level in a `type internal` group                | accepted       |
| protocol, group, and neighbor level in a `virtual-router` instance | accepted       |
| protocol, group, and neighbor level in a `vrf` instance            | accepted       |
| protocol, group, and neighbor level in a logical system            | accepted       |
| `family inet unicast` at the protocol, group, or neighbor level    | `syntax error` |
| `group <g> neighbor <n> multihop`                                  | `syntax error` |
| `protocols bgp traceoptions`                                       | `syntax error` |
| `routing-options`                                                  | `syntax error` |

### Values

Both statements take one unsigned 32-bit byte count. `k`, `m`, and `g`
multiply by 1024, 1048576, and 1073741824. Rejected values fail when the
`set` line is parsed; every accepted value passes `commit check`.
`send-buffer` matched `receive-buffer` for every value tried on both.

| Value                   | Result                                                   | Displayed as     |
| ----------------------- | -------------------------------------------------------- | ---------------- |
| `64k`                   | accepted                                                 | `64k`            |
| `64K`                   | accepted                                                 | `64k`            |
| `65536`                 | accepted                                                 | `64k`            |
| `0x10000`               | accepted                                                 | `64k`            |
| `4096`                  | accepted                                                 | `4k`             |
| `1024k`                 | accepted                                                 | `1m`             |
| `2147483648`            | accepted                                                 | `2g`             |
| `1M`, `1g`, `3g`        | accepted                                                 | `1m`, `1g`, `3g` |
| `1000k`                 | accepted                                                 | `1000k`          |
| `1023k`                 | accepted                                                 | `1023k`          |
| `1025k`                 | accepted                                                 | `1049600`        |
| `1536k`                 | accepted                                                 | `1572864`        |
| `1025m`                 | accepted                                                 | `1074790400`     |
| `65537`, `1500`, `1000` | accepted                                                 | unchanged        |
| `0`, `0k`               | accepted                                                 | `0`              |
| `010`                   | accepted (octal)                                         | `8`              |
| `4294967295`            | accepted                                                 | `4294967295`     |
| `4294967296`            | `Value 4294967296 is not within range (0..4294967295)`   |                  |
| `4g`                    | `Value 4g is not within range (0..4294967295)`           |                  |
| `08`                    | `Invalid data '8' for octal number`                      |                  |
| `64kb`                  | `Invalid trailing data 'b' for numeric value: '64kb'`    |                  |
| `1t`                    | `Invalid trailing data 't' for numeric value: '1t'`      |                  |
| `64.5k`                 | `Invalid trailing data '.5k' for numeric value: '64.5k'` |                  |
| `-1`                    | `Invalid numeric value: '-1'`                            |                  |
| `abc`                   | `Invalid numeric value: 'abc'`                           |                  |
| (none)                  | `error: syntax error, expecting <data>: receive-buffer`  |                  |
| `64k 128k`              | `syntax error.`                                          |                  |

Junos displays a value with the largest suffix that divides it exactly
and leaves a quotient below 1024, and otherwise as plain bytes. The
same form appears in `show configuration`, `display set`, `display
xml`, and `display json` (as a string, `"receive-buffer" : "64k"`).
Within each hierarchy level, `display set` lists `send-buffer` before
`receive-buffer`, regardless of entry order.

### Effective sizes

`show bgp neighbor` reports `Receive Bufsize` and `Send Bufsize` when
the corresponding buffer is set and non-zero; neither appears in
`show bgp group`. The neighbor level overrides the group level, which
overrides the protocol level, and the two directions inherit
independently. Measured on the master session, one commit at a time:

| Configured on dut                                      | `show bgp neighbor 192.0.2.1`                          |
| ------------------------------------------------------ | ------------------------------------------------------ |
| protocol 64k, group 128k, neighbor 256k                | `Receive Bufsize: 262144 Send Bufsize: 262144`         |
| protocol 64k, group 128k                               | `Receive Bufsize: 131072 Send Bufsize: 131072`         |
| protocol 64k                                           | `Receive Bufsize: 65536 Send Bufsize: 65536`           |
| protocol `receive-buffer 64k` only                     | `Receive Bufsize: 65536`                               |
| neighbor `send-buffer 256k` only                       | `Send Bufsize: 262144`                                 |
| neighbor `send-buffer 0`, `receive-buffer 1000`        | `Receive Bufsize: 1000`                                |
| neighbor `send-buffer 1g`, `receive-buffer 4294967295` | `Receive Bufsize: 4294967295 Send Bufsize: 1073741824` |
| neighbor `send-buffer 16m`, `receive-buffer 1`         | `Receive Bufsize: 1 Send Bufsize: 16777216`            |
| none                                                   | (no Bufsize line)                                      |

Every commit that changed an effective buffer size reset the session
(new TCP source port, Up/Down time restarted). With a 1-byte receive
buffer the session re-established and dut installed 203.0.113.0/24.

### Batfish

Batfish reports each buffer line as unrecognized syntax. dut's neighbor
statements in `display set` form are only the buffer lines, so Batfish
defines neither neighbor and has no sessions on dut.
`test_main_rib_routes[dut]` and `test_bgp_rib_routes[dut]` are
sickbayed to batfish/batfish#10375.

## Raw output

Command lines start with `===== dut>` (operational mode) or
`===== dut#` (configuration mode). Device output is verbatim; `-----`
lines are labels.

Committing the six statements above, plus the same three levels in VR1,
on the live sessions (the startup config at the time had no buffer
statements). Output is truncated after `Up/Down Time`:

```
===== dut# commit
commit complete

===== dut> show bgp neighbor 192.0.2.1
Peer: 192.0.2.1+34689 AS 65002 Local: 192.0.2.0+179 AS 65001
  Group: TEST                  Routing-Instance: master
  Forwarding routing-instance: master
  Type: External    State: Established    Flags: <Sync>
  Last State: OpenConfirm   Last Event: RecvKeepAlive
  Last Error: None
  Options: <PeerAS Refresh>
  Options: <GracefulShutdownRcv>
  Holdtime: 90 Preference: 170
  Graceful Shutdown Receiver local-preference: 0
  Receive Bufsize: 262144 Send Bufsize: 262144
  Number of flaps: 0
  Up/Down Time : 20
```

The same command before the commit, truncated at the same line:

```
===== dut> show bgp neighbor 192.0.2.1
Peer: 192.0.2.1+33851 AS 65002 Local: 192.0.2.0+179 AS 65001
  Group: TEST                  Routing-Instance: master
  Forwarding routing-instance: master
  Type: External    State: Established    Flags: <Sync>
  Last State: OpenConfirm   Last Event: RecvKeepAlive
  Last Error: Cease
  Options: <PeerAS Refresh>
  Options: <GracefulShutdownRcv>
  Holdtime: 90 Preference: 170
  Graceful Shutdown Receiver local-preference: 0
  Number of flaps: 0
  Up/Down Time : 5:07
```

```
===== dut> show configuration protocols bgp
group TEST {
    type external;
    send-buffer 128k;
    receive-buffer 128k;
    peer-as 65002;
    neighbor 192.0.2.1 {
        send-buffer 256k;
        receive-buffer 256k;
    }
}
send-buffer 64k;
receive-buffer 64k;

===== dut> show configuration protocols bgp | display xml
<rpc-reply xmlns:junos="http://xml.juniper.net/junos/25.4R1.12/junos">
    <configuration junos:commit-seconds="1790898305" junos:commit-localtime="2026-10-01 23:45:05 UTC" junos:commit-user="admin">
            <protocols>
                <bgp>
                    <group>
                        <name>TEST</name>
                        <type>external</type>
                        <undocumented><send-buffer>128k</send-buffer></undocumented>
                        <undocumented><receive-buffer>128k</receive-buffer></undocumented>
                        <peer-as>65002</peer-as>
                        <neighbor>
                            <name>192.0.2.1</name>
                            <undocumented><send-buffer>256k</send-buffer></undocumented>
                            <undocumented><receive-buffer>256k</receive-buffer></undocumented>
                        </neighbor>
                    </group>
                    <undocumented><send-buffer>64k</send-buffer></undocumented>
                    <undocumented><receive-buffer>64k</receive-buffer></undocumented>
                </bgp>
            </protocols>
    </configuration>
    <cli>
        <banner></banner>
    </cli>
</rpc-reply>
```

VR1 after loading the startup config, which spells the sizes `65536`,
`128K`, and `0x40000`:

```
===== dut> show configuration | display set | match buffer
set routing-instances VR1 protocols bgp group TEST send-buffer 128k
set routing-instances VR1 protocols bgp group TEST receive-buffer 128k
set routing-instances VR1 protocols bgp group TEST neighbor 198.51.100.1 send-buffer 256k
set routing-instances VR1 protocols bgp group TEST neighbor 198.51.100.1 receive-buffer 256k
set routing-instances VR1 protocols bgp send-buffer 64k
set routing-instances VR1 protocols bgp receive-buffer 64k
set protocols bgp group TEST send-buffer 128k
set protocols bgp group TEST receive-buffer 128k
set protocols bgp group TEST neighbor 192.0.2.1 send-buffer 256k
set protocols bgp group TEST neighbor 192.0.2.1 receive-buffer 256k
set protocols bgp send-buffer 64k
set protocols bgp receive-buffer 64k
```

Normalization of entered values. Each value was entered alone, followed
by `show | compare`, `commit check`, and `rollback 0`:

```
===== dut# set protocols bgp receive-buffer 1536k

----- show | compare
[edit protocols bgp]
+   receive-buffer 1572864;
----- commit check
configuration check succeeds

===== dut# set protocols bgp receive-buffer 010

----- show | compare
[edit protocols bgp]
+   receive-buffer 8;
----- commit check
configuration check succeeds

===== dut# set protocols bgp receive-buffer 4294967296
^
Value 4294967296 is not within range (0..4294967295) at '4294967296'
----- show | compare

----- commit check
configuration check succeeds
```

## Checks

`checks.yaml` verifies both sessions and routes, uses
`bgp_peer_bufsize` to assert that each session reports the
neighbor-level 262144 bytes in both directions, and runs the commit
checks in the hierarchy and value tables on dut.
