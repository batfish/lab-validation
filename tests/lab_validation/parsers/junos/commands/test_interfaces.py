import json

from lab_validation.parsers.junos.commands.interfaces import (
    _get_admin,
    _get_admin_logical,
    _get_line,
    _to_bandwidth,
    parse_show_interfaces_json,
)
from lab_validation.parsers.junos.models.interfaces import (
    JunosInterface,
    JunosInterfaceState,
)


def test_get_admin() -> None:
    text_up = "up"
    status_up = _get_admin(text_up)
    assert status_up is True
    text_down = "down"
    status_down = _get_admin(text_down)
    assert status_down is False


def test_get_line() -> None:
    text_up = "up"
    status_up = _get_line(text_up)
    assert status_up is True
    text_down = "down"
    status_down = _get_line(text_down)
    assert status_down is False


def test_parse_show_interfaces_json_only_physical() -> None:
    """
    Testing ony physical interface parsing
    """

    text = """
    {
    "interface-information" : [
    {
        "attributes" : {"xmlns" : "http://xml.juniper.net/junos/17.4R1/junos-interface",
                        "junos:style" : "normal"
                       },
        "physical-interface" : [
        {
            "name" : [
            {
                "data" : "gr-0/0/0"
            }
            ],
            "admin-status" : [
            {
                "data" : "up",
                "attributes" : {"junos:format" : "Enabled"}
            }
            ],
            "oper-status" : [
            {
                "data" : "up"
            }
            ],
            "local-index" : [
            {
                "data" : "645"
            }
            ],
            "snmp-index" : [
            {
                "data" : "504"
            }
            ],
            "if-type" : [
            {
                "data" : "GRE"
            }
            ],
            "link-level-type" : [
            {
                "data" : "GRE"
            }
            ],
            "mtu" : [
            {
                "data" : "Unlimited"
            }
            ],
            "speed" : [
            {
                "data" : "800mbps"
            }
            ],
            "if-device-flags" : [
            {
                "ifdf-present" : [
                {
                    "data" : [null]
                }
                ],
                "ifdf-running" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "ifd-specific-config-flags" : [
            {
            }
            ],
            "if-config-flags" : [
            {
                "iff-point-to-point" : [
                {
                    "data" : [null]
                }
                ],
                "iff-snmp-traps" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "traffic-statistics" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "input-bps" : [
                {
                    "data" : "0"
                }
                ],
                "input-pps" : [
                {
                    "data" : "0"
                }
                ],
                "output-bps" : [
                {
                    "data" : "0"
                }
                ],
                "output-pps" : [
                {
                    "data" : "0"
                }
                ]
            }
            ]
        }
        ]
    }
    ]
}

{master:0}
    """

    interfaces = parse_show_interfaces_json(text)
    assert interfaces == [
        JunosInterface(
            name="gr-0/0/0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=_to_bandwidth("800mbps"),
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Physical interface",
        )
    ]


def test_parse_show_interfaces_json_physical_logical() -> None:
    """
    Testing physical interface and it's logical interface
    """

    text = """
    {
    "interface-information" : [
    {
        "attributes" : {"xmlns" : "http://xml.juniper.net/junos/17.4R1/junos-interface",
                        "junos:style" : "normal"
                       },
        "physical-interface" : [
        {
            "name" : [
            {
                "data" : "xe-0/0/0"
            }
            ],
            "admin-status" : [
            {
                "data" : "up",
                "attributes" : {"junos:format" : "Enabled"}
            }
            ],
            "oper-status" : [
            {
                "data" : "up"
            }
            ],
            "local-index" : [
            {
                "data" : "649"
            }
            ],
            "snmp-index" : [
            {
                "data" : "528"
            }
            ],
            "link-level-type" : [
            {
                "data" : "Ethernet"
            }
            ],
            "mtu" : [
            {
                "data" : "1514"
            }
            ],
            "sonet-mode" : [
            {
                "data" : "LAN-PHY"
            }
            ],
            "source-filtering" : [
            {
                "data" : "disabled"
            }
            ],
            "speed" : [
            {
                "data" : "10Gbps"
            }
            ],
            "duplex" : [
            {
                "data" : "Full-Duplex"
            }
            ],
            "eth-switch-error" : [
            {
                "data" : "none"
            }
            ],
            "bpdu-error" : [
            {
                "data" : "none"
            }
            ],
            "ld-pdu-error" : [
            {
                "data" : "none"
            }
            ],
            "eth-switch-error" : [
            {
                "data" : "none"
            }
            ],
            "l2pt-error" : [
            {
                "data" : "none"
            }
            ],
            "loopback" : [
            {
                "data" : "disabled"
            }
            ],
            "if-flow-control" : [
            {
                "data" : "disabled"
            }
            ],
            "if-media-type" : [
            {
                "data" : "Fiber"
            }
            ],
            "if-device-flags" : [
            {
                "ifdf-present" : [
                {
                    "data" : [null]
                }
                ],
                "ifdf-running" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "if-config-flags" : [
            {
                "iff-snmp-traps" : [
                {
                    "data" : [null]
                }
                ],
                "internal-flags" : [
                {
                    "data" : "0x4000"
                }
                ]
            }
            ],
            "if-media-flags" : [
            {
                "ifmf-none" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "physical-interface-cos-information" : [
            {
                "physical-interface-cos-hw-max-queues" : [
                {
                    "data" : "8"
                }
                ],
                "physical-interface-cos-use-max-queues" : [
                {
                    "data" : "8"
                }
                ]
            }
            ],
            "current-physical-address" : [
            {
                "data" : "02:05:86:71:a0:03"
            }
            ],
            "hardware-physical-address" : [
            {
                "data" : "02:05:86:71:a0:03"
            }
            ],
            "interface-flapped" : [
            {
                "data" : "2019-11-14 18:02:03 UTC (1d 03:19 ago)",
                "attributes" : {"junos:seconds" : "98347"}
            }
            ],
            "traffic-statistics" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "input-bps" : [
                {
                    "data" : "0"
                }
                ],
                "input-pps" : [
                {
                    "data" : "0"
                }
                ],
                "output-bps" : [
                {
                    "data" : "0"
                }
                ],
                "output-pps" : [
                {
                    "data" : "0"
                }
                ]
            }
            ],
            "active-alarms" : [
            {
                "interface-alarms" : [
                {
                    "alarm-not-present" : [
                    {
                        "data" : [null]
                    }
                    ]
                }
                ]
            }
            ],
            "active-defects" : [
            {
                "interface-alarms" : [
                {
                    "alarm-not-present" : [
                    {
                        "data" : [null]
                    }
                    ]
                }
                ]
            }
            ],
            "ethernet-pcs-statistics" : [
            {
                "attributes" : {"junos:style" : "verbose"},
                "bit-error-seconds" : [
                {
                    "data" : "0"
                }
                ],
                "errored-blocks-seconds" : [
                {
                    "data" : "0"
                }
                ]
            }
            ],
            "ethernet-fec-mode" : [
            {
                "attributes" : {"junos:style" : "verbose"},
                "enabled_fec_mode" : [
                {
                }
                ]
            }
            ],
            "ethernet-fec-statistics" : [
            {
                "attributes" : {"junos:style" : "verbose"},
                "fec_ccw_count" : [
                {
                    "data" : "0"
                }
                ],
                "fec_nccw_count" : [
                {
                    "data" : "0"
                }
                ],
                "fec_ccw_error_rate" : [
                {
                    "data" : "0"
                }
                ],
                "fec_nccw_error_rate" : [
                {
                    "data" : "0"
                }
                ]
            }
            ],
            "interface-transmit-statistics" : [
            {
                "data" : "Disabled"
            }
            ],
            "logical-interface" : [
            {
                "name" : [
                {
                    "data" : "xe-0/0/0.0"
                }
                ],
                "local-index" : [
                {
                    "data" : "571"
                }
                ],
                "snmp-index" : [
                {
                    "data" : "541"
                }
                ],
                "if-config-flags" : [
                {
                    "iff-up" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "internal-flags" : [
                    {
                        "data" : "0x4004000"
                    }
                    ]
                }
                ],
                "encapsulation" : [
                {
                    "data" : "ENET2"
                }
                ],
                "policer-overhead" : [
                {
                }
                ],
                "traffic-statistics" : [
                {
                    "attributes" : {"junos:style" : "brief"},
                    "input-packets" : [
                    {
                        "data" : "11594"
                    }
                    ],
                    "output-packets" : [
                    {
                        "data" : "8359"
                    }
                    ]
                }
                ],
                "filter-information" : [
                {
                }
                ],
                "address-family" : [
                {
                    "address-family-name" : [
                    {
                        "data" : "inet"
                    }
                    ],
                    "mtu" : [
                    {
                        "data" : "1500"
                    }
                    ],
                    "max-local-cache" : [
                    {
                        "data" : "75000"
                    }
                    ],
                    "new-hold-limit" : [
                    {
                        "data" : "75000"
                    }
                    ],
                    "intf-curr-cnt" : [
                    {
                        "data" : "1"
                    }
                    ],
                    "intf-unresolved-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-dropcnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "address-family-flags" : [
                    {
                        "ifff-sendbcast-pkt-to-re" : [
                        {
                            "data" : [null]
                        }
                        ]
                    }
                    ],
                    "interface-address" : [
                    {
                        "ifa-flags" : [
                        {
                            "ifaf-current-preferred" : [
                            {
                                "data" : [null]
                            }
                            ],
                            "ifaf-current-primary" : [
                            {
                                "data" : [null]
                            }
                            ]
                        }
                        ],
                        "ifa-destination" : [
                        {
                            "data" : "10.10.50/24"
                        }
                        ],
                        "ifa-local" : [
                        {
                            "data" : "10.10.50.2"
                        }
                        ],
                        "ifa-broadcast" : [
                        {
                            "data" : "10.10.50.255"
                        }
                        ]
                    }
                    ]
                }
                ]
            }
            ]
        }
        ]
    }
    ]
}

{master:0}
    """

    interfaces = parse_show_interfaces_json(text)
    assert interfaces == [
        JunosInterface(
            name="xe-0/0/0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=_to_bandwidth("10Gbps"),
            bandwidth=None,
            mtu="1514",
            interface_type="Physical interface",
        ),
        JunosInterface(
            name="xe-0/0/0.0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=_to_bandwidth("10Gbps"),
            bandwidth=None,
            mtu="1500",
            interface_type="Logical interface",
        ),
    ]


def test_parse_show_interfaces_json_physical_multiple_logical() -> None:
    """
    Testing physical interface with multiple logical interfaces
    """

    text = """
    {
    "interface-information" : [
    {
        "attributes" : {"xmlns" : "http://xml.juniper.net/junos/17.4R1/junos-interface",
                        "junos:style" : "normal"
                       },
        "physical-interface" : [
        {
            "name" : [
            {
                "data" : "lo0"
            }
            ],
            "admin-status" : [
            {
                "data" : "up",
                "attributes" : {"junos:format" : "Enabled"}
            }
            ],
            "oper-status" : [
            {
                "data" : "up"
            }
            ],
            "local-index" : [
            {
                "data" : "6"
            }
            ],
            "snmp-index" : [
            {
                "data" : "6"
            }
            ],
            "if-type" : [
            {
                "data" : "Loopback"
            }
            ],
            "mtu" : [
            {
                "data" : "Unlimited"
            }
            ],
            "if-device-flags" : [
            {
                "ifdf-present" : [
                {
                    "data" : [null]
                }
                ],
                "ifdf-running" : [
                {
                    "data" : [null]
                }
                ],
                "ifdf-loopback" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "ifd-specific-config-flags" : [
            {
            }
            ],
            "if-config-flags" : [
            {
                "iff-snmp-traps" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "if-media-flags" : [
            {
                "ifmf-none" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "interface-flapped" : [
            {
                "data" : "Never",
                "attributes" : {"junos:seconds" : "0"}
            }
            ],
            "traffic-statistics" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "input-packets" : [
                {
                    "data" : "2630502"
                }
                ],
                "output-packets" : [
                {
                    "data" : "2630502"
                }
                ]
            }
            ],
            "logical-interface" : [
            {
                "name" : [
                {
                    "data" : "lo0.0"
                }
                ],
                "local-index" : [
                {
                    "data" : "552"
                }
                ],
                "snmp-index" : [
                {
                    "data" : "16"
                }
                ],
                "if-config-flags" : [
                {
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ]
                }
                ],
                "encapsulation" : [
                {
                    "data" : "Unspecified"
                }
                ],
                "policer-overhead" : [
                {
                }
                ],
                "traffic-statistics" : [
                {
                    "attributes" : {"junos:style" : "brief"},
                    "input-packets" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "output-packets" : [
                    {
                        "data" : "0"
                    }
                    ]
                }
                ],
                "filter-information" : [
                {
                }
                ],
                "address-family" : [
                {
                    "address-family-name" : [
                    {
                        "data" : "inet"
                    }
                    ],
                    "mtu" : [
                    {
                        "data" : "Unlimited"
                    }
                    ],
                    "max-local-cache" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "new-hold-limit" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-curr-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-unresolved-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-dropcnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "address-family-flags" : [
                    {
                        "ifff-sendbcast-pkt-to-re" : [
                        {
                            "data" : [null]
                        }
                        ]
                    }
                    ],
                    "interface-address" : [
                    {
                        "ifa-flags" : [
                        {
                            "ifaf-current-default" : [
                            {
                                "data" : [null]
                            }
                            ],
                            "ifaf-current-primary" : [
                            {
                                "data" : [null]
                            }
                            ]
                        }
                        ],
                        "ifa-local" : [
                        {
                            "data" : "192.168.123.6"
                        }
                        ]
                    }
                    ]
                },
                {
                    "address-family-name" : [
                    {
                        "data" : "inet6"
                    }
                    ],
                    "mtu" : [
                    {
                        "data" : "Unlimited"
                    }
                    ],
                    "max-local-cache" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "new-hold-limit" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-curr-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-unresolved-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-dropcnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "address-family-flags" : [
                    {
                        "ifff-none" : [
                        {
                            "data" : [null]
                        }
                        ]
                    }
                    ],
                    "interface-address" : [
                    {
                        "ifa-flags" : [
                        {
                            "internal-flags" : [
                            {
                                "data" : "0x800"
                            }
                            ]
                        }
                        ],
                        "ifa-local" : [
                        {
                            "data" : "fe80::205:860f:fc71:a000"
                        }
                        ],
                        "interface-address" : [
                        {
                            "in6-addr-flags" : [
                            {
                                "ifaf-none" : [
                                {
                                    "data" : [null]
                                }
                                ]
                            }
                            ]
                        }
                        ]
                    }
                    ]
                }
                ]
            },
            {
                "name" : [
                {
                    "data" : "lo0.10"
                }
                ],
                "local-index" : [
                {
                    "data" : "553"
                }
                ],
                "snmp-index" : [
                {
                    "data" : "510"
                }
                ],
                "if-config-flags" : [
                {
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ]
                }
                ],
                "encapsulation" : [
                {
                    "data" : "Unspecified"
                }
                ],
                "policer-overhead" : [
                {
                }
                ],
                "traffic-statistics" : [
                {
                    "attributes" : {"junos:style" : "brief"},
                    "input-packets" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "output-packets" : [
                    {
                        "data" : "0"
                    }
                    ]
                }
                ],
                "filter-information" : [
                {
                }
                ],
                "address-family" : [
                {
                    "address-family-name" : [
                    {
                        "data" : "inet"
                    }
                    ],
                    "mtu" : [
                    {
                        "data" : "Unlimited"
                    }
                    ],
                    "max-local-cache" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "new-hold-limit" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-curr-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-unresolved-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-dropcnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "address-family-flags" : [
                    {
                        "ifff-sendbcast-pkt-to-re" : [
                        {
                            "data" : [null]
                        }
                        ]
                    }
                    ],
                    "interface-address" : [
                    {
                        "ifa-flags" : [
                        {
                            "ifaf-current-default" : [
                            {
                                "data" : [null]
                            }
                            ],
                            "ifaf-current-primary" : [
                            {
                                "data" : [null]
                            }
                            ]
                        }
                        ],
                        "ifa-local" : [
                        {
                            "data" : "1.1.6.10"
                        }
                        ]
                    }
                    ]
                }
                ]
            },
            {
                "name" : [
                {
                    "data" : "lo0.20"
                }
                ],
                "local-index" : [
                {
                    "data" : "554"
                }
                ],
                "snmp-index" : [
                {
                    "data" : "511"
                }
                ],
                "if-config-flags" : [
                {
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ]
                }
                ],
                "encapsulation" : [
                {
                    "data" : "Unspecified"
                }
                ],
                "policer-overhead" : [
                {
                }
                ],
                "traffic-statistics" : [
                {
                    "attributes" : {"junos:style" : "brief"},
                    "input-packets" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "output-packets" : [
                    {
                        "data" : "0"
                    }
                    ]
                }
                ],
                "filter-information" : [
                {
                }
                ],
                "address-family" : [
                {
                    "address-family-name" : [
                    {
                        "data" : "inet"
                    }
                    ],
                    "mtu" : [
                    {
                        "data" : "Unlimited"
                    }
                    ],
                    "max-local-cache" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "new-hold-limit" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-curr-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-unresolved-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-dropcnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "address-family-flags" : [
                    {
                        "ifff-sendbcast-pkt-to-re" : [
                        {
                            "data" : [null]
                        }
                        ]
                    }
                    ],
                    "interface-address" : [
                    {
                        "ifa-flags" : [
                        {
                            "ifaf-current-default" : [
                            {
                                "data" : [null]
                            }
                            ],
                            "ifaf-current-primary" : [
                            {
                                "data" : [null]
                            }
                            ]
                        }
                        ],
                        "ifa-local" : [
                        {
                            "data" : "1.1.6.20"
                        }
                        ]
                    }
                    ]
                }
                ]
            },
            {
                "name" : [
                {
                    "data" : "lo0.16385"
                }
                ],
                "local-index" : [
                {
                    "data" : "555"
                }
                ],
                "snmp-index" : [
                {
                    "data" : "22"
                }
                ],
                "if-config-flags" : [
                {
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ]
                }
                ],
                "encapsulation" : [
                {
                    "data" : "Unspecified"
                }
                ],
                "policer-overhead" : [
                {
                }
                ],
                "traffic-statistics" : [
                {
                    "attributes" : {"junos:style" : "brief"},
                    "input-packets" : [
                    {
                        "data" : "2630399"
                    }
                    ],
                    "output-packets" : [
                    {
                        "data" : "2630399"
                    }
                    ]
                }
                ],
                "filter-information" : [
                {
                }
                ],
                "address-family" : [
                {
                    "address-family-name" : [
                    {
                        "data" : "inet"
                    }
                    ],
                    "mtu" : [
                    {
                        "data" : "Unlimited"
                    }
                    ],
                    "max-local-cache" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "new-hold-limit" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-curr-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-unresolved-cnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "intf-dropcnt" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "address-family-flags" : [
                    {
                        "ifff-none" : [
                        {
                            "data" : [null]
                        }
                        ]
                    }
                    ]
                }
                ]
            }
            ]
        }
        ]
    }
    ]
}

{master:0}
    """

    interfaces = parse_show_interfaces_json(text)
    assert interfaces == [
        JunosInterface(
            name="lo0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=None,
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Physical interface",
        ),
        JunosInterface(
            name="lo0.0",
            state=JunosInterfaceState(admin=True, line=True),
            speed=None,
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Logical interface",
        ),
        JunosInterface(
            name="lo0.10",
            state=JunosInterfaceState(admin=True, line=True),
            speed=None,
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Logical interface",
        ),
        JunosInterface(
            name="lo0.20",
            state=JunosInterfaceState(admin=True, line=True),
            speed=None,
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Logical interface",
        ),
        JunosInterface(
            name="lo0.16385",
            state=JunosInterfaceState(admin=True, line=True),
            speed=None,
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Logical interface",
        ),
    ]


def test_parse_show_interfaces_json_admin_up_line_down() -> None:
    """
    Testing ony physical interface parsing
    """

    text = """
    {
    "interface-information" : [
    {
        "attributes" : {"xmlns" : "http://xml.juniper.net/junos/17.4R1/junos-interface",
                        "junos:style" : "normal"
                       },
        "physical-interface" : [
        {
            "name" : [
            {
                "data" : "gr-0/0/0"
            }
            ],
            "admin-status" : [
            {
                "data" : "up",
                "attributes" : {"junos:format" : "Enabled"}
            }
            ],
            "oper-status" : [
            {
                "data" : "down"
            }
            ],
            "local-index" : [
            {
                "data" : "645"
            }
            ],
            "snmp-index" : [
            {
                "data" : "504"
            }
            ],
            "if-type" : [
            {
                "data" : "GRE"
            }
            ],
            "link-level-type" : [
            {
                "data" : "GRE"
            }
            ],
            "mtu" : [
            {
                "data" : "Unlimited"
            }
            ],
            "speed" : [
            {
                "data" : "800mbps"
            }
            ],
            "if-device-flags" : [
            {
                "ifdf-present" : [
                {
                    "data" : [null]
                }
                ],
                "ifdf-running" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "ifd-specific-config-flags" : [
            {
            }
            ],
            "if-config-flags" : [
            {
                "iff-point-to-point" : [
                {
                    "data" : [null]
                }
                ],
                "iff-snmp-traps" : [
                {
                    "data" : [null]
                }
                ]
            }
            ],
            "traffic-statistics" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "input-bps" : [
                {
                    "data" : "0"
                }
                ],
                "input-pps" : [
                {
                    "data" : "0"
                }
                ],
                "output-bps" : [
                {
                    "data" : "0"
                }
                ],
                "output-pps" : [
                {
                    "data" : "0"
                }
                ]
            }
            ]
        }
        ]
    }
    ]
}

{master:0}
    """

    interfaces = parse_show_interfaces_json(text)
    assert interfaces == [
        JunosInterface(
            name="gr-0/0/0",
            state=JunosInterfaceState(admin=True, line=False),
            speed=_to_bandwidth("800mbps"),
            bandwidth=None,
            mtu="Unlimited",
            interface_type="Physical interface",
        )
    ]


def test_get_admin_logical() -> None:
    """
    Testing logical admin and line with value "iff-up"
    """

    text = """
    {
                "if-config-flags" : [
                {
                    "iff-up" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "internal-flags" : [
                    {
                        "data" : "0x4004000"
                    }
                    ]
                }
                ]
    }
    """
    admin_physical = False
    line_physical = True
    text = json.loads(text)
    text = text["if-config-flags"][0]
    assert _get_admin_logical(text, admin_physical, line_physical) == (True, True)

    """
    Testing logical admin and line with value "iff-down"
    """

    text = """
    {
                "if-config-flags" : [
                {
                    "iff-down" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "internal-flags" : [
                    {
                        "data" : "0x4004000"
                    }
                    ]
                }
                ]
    }
    """
    admin_physical = False
    line_physical = True
    text = json.loads(text)
    text = text["if-config-flags"][0]
    assert _get_admin_logical(text, admin_physical, line_physical) == (False, False)

    """
    Testing logical admin and line being inherited from physical
    """

    text = """
    {
                "if-config-flags" : [
                {
                    "iff-snmp-traps" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "internal-flags" : [
                    {
                        "data" : "0x4004000"
                    }
                    ]
                }
                ]
    }
    """
    admin_physical = False
    line_physical = True
    text = json.loads(text)
    text = text["if-config-flags"][0]
    assert _get_admin_logical(text, admin_physical, line_physical) == (False, True)


def test_to_bandwidth() -> None:
    assert _to_bandwidth("") is None
    assert _to_bandwidth("1kbps") == 1000
    assert _to_bandwidth("1mbps") == 1000000
    assert _to_bandwidth("1gbps") == 1000000000
    assert _to_bandwidth(None) is None
    assert _to_bandwidth("1KBPS") == 1000
