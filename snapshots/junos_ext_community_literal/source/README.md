# Junos Extended-Community Literal Lab

Confirms how Junos interprets the generic extended-community literal
`members 65000:672277L:36867`, a syntax seen in real configs whose
high-order `65000` "type" is non-obvious.

## The syntax

Junos accepts extended communities in a generic `type:admin:admin`
form in addition to the named forms (`target:…`, `origin:…`). For the
mystery value:

| Field     | Value       | Bytes | Meaning                              |
| --------- | ----------- | ----- | ------------------------------------ |
| `65000`   | 0xFDE8      | 2     | type octet 0xFD, subtype octet 0xE8  |
| `672277L` | 0x000A_4215 | 4     | global administrator (L = 4-byte GA) |
| `36867`   | 0x9003      | 2     | local administrator (assigned number)|

The `L` suffix forces the global administrator into the 4-byte
AS-specific layout (type 0x02 family). Without it, a bare number ≤
0xFFFF would be a 2-byte global administrator.

The first field `65000` is **not** a route target or site-of-origin.
When it is a bare integer, Junos splits it into the two leading octets
of the 8-byte community: `65000 >> 8 = 0xFD` (type) and
`65000 & 0xFF = 0xE8` (subtype). 0xFD has both the IANA (0x80) and
non-transitive (0x40) bits set, which is why it does not resemble a
standard transitive route target (0x02:0x02).

## Topology

```
sender (AS 65001) --- receiver (AS 65002)
       ge-0/0/0  <->  ge-0/0/0
       10.0.12.0      10.0.12.1
```

## Test Routes

sender originates these static routes, tagging each via export policy:

| Prefix       | Community Applied         | Purpose                       |
| ------------ | ------------------------- | ----------------------------- |
| 10.10.0.0/24 | (none)                    | control                       |
| 10.10.1.0/24 | 65000:672277L:36867       | the mystery literal           |
| 10.10.2.0/24 | target:672277L:36867      | 4-byte-AS route target        |
| 10.10.3.0/24 | target:65000:36867        | 2-byte-AS route target        |

## Findings (confirmed on vJunos-router 25.4R1.12)

The syntax is exactly a generic 2:4:2-byte extended community literal,
as hypothesized. On the sender, `show route 10.10.1.0/24 extensive`
renders the configured `members 65000:672277L:36867` as:

```
Communities: unknown type 0xffe8:0xa4215:0x9003
```

Decoding:

- `0xa4215` = 672277 — the 4-byte global administrator (the `L` forces
  the 4-byte width; without it the value would have to fit in 2 bytes).
- `0x9003` = 36867 — the 2-byte local administrator.
- Type renders as `0xffe8`: the configured `65000` = 0xFDE8, with the
  0x02 bit set (`0xFD | 0x02 = 0xFF`) — the AS-specific-4-byte type bit
  that the `L` suffix selects. Junos classifies this as an **unknown
  type** because 0xFF:0xE8 is not an IANA-assigned extended-community
  type/subtype.

Wire behavior: because the type's transitivity bit marks it
non-transitive, Junos **strips the community at the eBGP boundary**.
The receiver sees `10.10.1.0/24` with no community at all, while the
comparison routes carrying `target:672277L:36867` (4-byte-AS RT) and
`target:65000:36867` (2-byte-AS RT) cross unchanged. The `L` suffix is
purely about global-administrator width, confirmed by the two RT rows.

## Batfish Notes

### Extended-community rendering

Batfish prints route targets in numeric type-prefix form rather than
with the Junos `target` keyword: `target:672277L:36867` becomes
`514:672277L:36867` (type 0x0202, 4-byte-AS) and `target:65000:36867`
becomes `2:65000:36867` (type 0x0002, 2-byte-AS). These are the same
communities in a different notation, so `JunosValidator` canonicalizes
the Junos `target:GA:LA` form to Batfish's numeric form before
comparing. Without that canonicalization the receiver's BGP routes
would mismatch on community form alone.

### Literal parse rejection (batfish/batfish#10018)

`ExtendedCommunity.parse` (flatjuniper) handles the `L` suffix (4-byte
GA) and splits a bare numeric first field into type/subtype octets.
But it computes the type via signed-byte arithmetic — `(byte) 0xFD` is
negative — and `ExtendedCommunity.of` rejects negative types. So a
`65000:…` literal (any type octet ≥ 0x80) fails literal parsing and
falls back to a **regex** community member. Initializing this snapshot
in Batfish yields the convert warning

```
FATAL: 'MYSTERY' community contains no non-wildcard members in an add action
```

i.e. the `community add MYSTERY` is dropped because the member was
parsed as a wildcard regex, not a literal. This does not fail a lab
test today — the community is stripped at the eBGP boundary on the real
device, so the receiver's routes carry no community on either side, and
the FATAL is a *convert* warning (not caught by `test_parse_warnings`,
which only checks *parse* warnings) on the sender. It is a genuine
parser gap tracked in batfish/batfish#10018.
