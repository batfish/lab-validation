from lab_validation.parsers.junos.commands.routes import (
    _parse_as_path_with_origin,
    _parse_evpn_type5_destination,
    convert_active,
    parse_show_route_display_json,
    parse_show_route_evpn_display_json,
)
from lab_validation.parsers.junos.models.routes import JunosEvpnRoute, JunosMainRibRoute


def test_show_route_display_json() -> None:
    text = """
    {
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [
            {
                "data" : "inet.0"
            }
            ],
            "rt" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "rt-destination" : [
                {
                    "data" : "10.10.10.0/24"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "current-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "last-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "BGP"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "170"
                    }
                    ],
                    "med" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "local-preference" : [
                    {
                        "data" : "100"
                    }
                    ],
                    "as-path" : [
                    {
                        "data" : "1 I"
                    }
                    ],
                    "validation-state" : [
                    {
                        "data" : "unverified"
                    }
                    ],
                    "nh" : [
                    {
                        "selected-next-hop" : [
                        {
                            "data" : [null]
                        }
                        ],
                        "to" : [
                        {
                            "data" : "10.10.50.1"
                        }
                        ],
                        "via" : [
                        {
                            "data" : "xe-0/0/0.0"
                        }
                        ]
                    }
                    ]
                }
                ]
            },
            {
                "attributes" : {"junos:style" : "brief"},
                "rt-destination" : [
                {
                    "data" : "10.10.50.0/24"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "Direct"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "nh" : [
                    {
                        "selected-next-hop" : [
                        {
                            "data" : [null]
                        }
                        ],
                        "via" : [
                        {
                            "data" : "xe-0/0/0.0"
                        }
                        ]
                    }
                    ]
                },
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "BGP"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "170"
                    }
                    ],
                    "med" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "local-preference" : [
                    {
                        "data" : "100"
                    }
                    ],
                    "as-path" : [
                    {
                        "data" : "1 I"
                    }
                    ],
                    "validation-state" : [
                    {
                        "data" : "unverified"
                    }
                    ],
                    "nh" : [
                    {
                        "selected-next-hop" : [
                        {
                            "data" : [null]
                        }
                        ],
                        "to" : [
                        {
                            "data" : "10.10.50.1"
                        }
                        ],
                        "via" : [
                        {
                            "data" : "xe-0/0/0.0"
                        }
                        ]
                    }
                    ]
                }
                ]
            },
            {
                "attributes" : {"junos:style" : "brief"},
                "rt-destination" : [
                {
                    "data" : "10.10.50.2/32"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "current-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "last-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "Local"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "nh-type" : [
                    {
                        "data" : "Local"
                    }
                    ],
                    "nh" : [
                    {
                        "nh-local-interface" : [
                        {
                            "data" : "xe-0/0/0.0"
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
            "table-name" : [
            {
                "data" : "cust10.inet.0"
            }
            ],
            "rt" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "rt-destination" : [
                {
                    "data" : "1.1.6.10/32"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "current-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "last-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "Direct"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "nh" : [
                    {
                        "selected-next-hop" : [
                        {
                            "data" : [null]
                        }
                        ],
                        "via" : [
                        {
                            "data" : "lo0.10"
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
            "table-name" : [
            {
                "data" : "cust20.inet.0"
            }
            ],
            "rt" : [
            {
                "rt-destination" : [
                {
                    "data" : "1.1.6.20/32"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "current-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "last-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "Direct"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "nh" : [
                    {
                        "selected-next-hop" : [
                        {
                            "data" : [null]
                        }
                        ],
                        "via" : [
                        {
                            "data" : "lo0.20"
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
            "table-name" : [
            {
                "data" : "inet6.0"
            }
            ],
            "destination-count" : [
            {
                "data" : "2"
            }
            ],
            "total-route-count" : [
            {
                "data" : "2"
            }
            ],
            "active-route-count" : [
            {
                "data" : "2"
            }
            ],
            "holddown-route-count" : [
            {
                "data" : "0"
            }
            ],
            "hidden-route-count" : [
            {
                "data" : "0"
            }
            ],
            "rt" : [
            {
                "attributes" : {"junos:style" : "brief"},
                "rt-destination" : [
                {
                    "data" : "ff02::2/128"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "current-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "last-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "INET6"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "0"
                    }
                    ],
                    "age" : [
                    {
                        "data" : "2d 02:38:51",
                        "attributes" : {"junos:seconds" : "182331"}
                    }
                    ],
                    "nh-type" : [
                    {
                        "data" : "MultiRecv"
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

    routes = parse_show_route_display_json(text)
    assert routes == [
        JunosMainRibRoute(
            vrf="default",
            network="10.10.10.0/24",
            protocol="BGP",
            admin=170,
            metric=0,
            next_hop_ip="10.10.50.1",
            next_hop_int="xe-0/0/0.0",
            nh_type=None,
            active=True,
        ),
        JunosMainRibRoute(
            vrf="default",
            network="10.10.50.0/24",
            protocol="Direct",
            admin=0,
            metric=None,
            next_hop_ip=None,
            next_hop_int="xe-0/0/0.0",
            nh_type=None,
            active=True,
        ),
        JunosMainRibRoute(
            vrf="default",
            network="10.10.50.0/24",
            protocol="BGP",
            admin=170,
            metric=0,
            next_hop_ip="10.10.50.1",
            next_hop_int="xe-0/0/0.0",
            nh_type=None,
            active=True,
        ),
        JunosMainRibRoute(
            vrf="default",
            network="10.10.50.2/32",
            protocol="Local",
            admin=0,
            metric=None,
            next_hop_ip=None,
            next_hop_int="xe-0/0/0.0",
            nh_type=None,
            active=True,
        ),
        JunosMainRibRoute(
            vrf="cust10",
            network="1.1.6.10/32",
            protocol="Direct",
            admin=0,
            metric=None,
            next_hop_ip=None,
            next_hop_int="lo0.10",
            nh_type=None,
            active=True,
        ),
        JunosMainRibRoute(
            vrf="cust20",
            network="1.1.6.20/32",
            protocol="Direct",
            admin=0,
            metric=None,
            next_hop_ip=None,
            next_hop_int="lo0.20",
            nh_type=None,
            active=True,
        ),
    ]


def test_show_route_display_json_static_null() -> None:
    text = """
{
  "route-information": [
    {
      "attributes": {
        "xmlns": "http://xml.juniper.net/junos/17.3R1/junos-routing"
      },
      "route-table": [
        {
          "comment": "keepalive",
          "table-name": [
            {
              "data": "DATA.inet.0"
            }
          ],
          "rt": [
            {
              "attributes": {
                "junos:style": "brief"
              },
              "rt-destination": [
                {
                  "data": "10.100.0.0/16"
                }
              ],
              "rt-entry": [
                {
                  "active-tag": [
                    {
                      "data": "*"
                    }
                  ],
                  "current-active": [
                    {
                      "data": [
                        null
                      ]
                    }
                  ],
                  "last-active": [
                    {
                      "data": [
                        null
                      ]
                    }
                  ],
                  "protocol-name": [
                    {
                      "data": "Static"
                    }
                  ],
                  "preference": [
                    {
                      "data": "5"
                    }
                  ],
                  "age": [
                    {
                      "data": "06:14:46",
                      "attributes": {
                        "junos:seconds": "22486"
                      }
                    }
                  ],
                  "nh-type": [
                    {
                      "data": "Discard"
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

    routes = parse_show_route_display_json(text)
    assert routes == [
        JunosMainRibRoute(
            vrf="DATA",
            network="10.100.0.0/16",
            protocol="Static",
            admin=5,
            metric=None,
            next_hop_ip=None,
            next_hop_int=None,
            nh_type="Discard",
            active=True,
        ),
    ]


def test_show_route_display_json_aggregate() -> None:
    text = """
{
  "route-information": [
    {
      "attributes": {
        "xmlns": "http://xml.juniper.net/junos/17.3R1/junos-routing"
      },
      "route-table": [
        {
          "comment": "keepalive",
          "table-name": [
            {
              "data": "DATA.inet.0"
            }
          ],
          "rt": [
            {
              "attributes": {
                "junos:style": "brief"
              },
              "rt-destination": [
                {
                  "data": "10.100.0.0/16"
                }
              ],
              "rt-entry": [
                {
                    "active-tag" : [
                    {
                        "data" : "*"
                    }
                    ],
                    "current-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "last-active" : [
                    {
                        "data" : [null]
                    }
                    ],
                    "protocol-name" : [
                    {
                        "data" : "Aggregate"
                    }
                    ],
                    "preference" : [
                    {
                        "data" : "130"
                    }
                    ],
                    "age" : [
                    {
                        "data" : "00:00:46",
                        "attributes" : {"junos:seconds" : "46"}
                    }
                    ],
                    "nh-type" : [
                    {
                        "data" : "Reject"
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

    routes = parse_show_route_display_json(text)
    assert routes == [
        JunosMainRibRoute(
            vrf="DATA",
            network="10.100.0.0/16",
            protocol="Aggregate",
            admin=130,
            metric=None,
            next_hop_ip=None,
            next_hop_int=None,
            nh_type="Reject",
            active=True,
        ),
    ]


def test_show_route_display_json_multiple_routes() -> None:
    # Test multiple routes from different next hop
    text = """
{
   "route-information" : [
   {
       "attributes" : {"xmlns" : "http://xml.juniper.net/junos/17.4R1/junos-routing"},
       "route-table" : [
       {
           "comment" : "keepalive",
           "table-name" : [
           {
               "data" : "inet.0"
           }
           ],
           "destination-count" : [
           {
               "data" : "27"
           }
           ],
           "total-route-count" : [
           {
               "data" : "33"
           }
           ],
           "active-route-count" : [
           {
               "data" : "27"
           }
           ],
           "holddown-route-count" : [
           {
               "data" : "0"
           }
           ],
           "hidden-route-count" : [
           {
               "data" : "0"
           }
           ],
           "rt" : [
           {
               "attributes" : {"junos:style" : "brief"},
               "rt-destination" : [
               {
                   "data" : "192.168.123.2/32"
               }
               ],
               "rt-entry" : [
               {
                   "active-tag" : [
                   {
                       "data" : "*"
                   }
                   ],
                   "current-active" : [
                   {
                       "data" : [null]
                   }
                   ],
                   "last-active" : [
                   {
                       "data" : [null]
                   }
                   ],
                   "protocol-name" : [
                   {
                       "data" : "BGP"
                   }
                   ],
                   "preference" : [
                   {
                       "data" : "170"
                   }
                   ],
                   "age" : [
                   {
                       "data" : "00:02:15",
                       "attributes" : {"junos:seconds" : "135"}
                   }
                   ],
                   "local-preference" : [
                   {
                       "data" : "100"
                   }
                   ],
                   "as-path" : [
                   {
                       "data" : "65002 I"
                   }
                   ],
                   "validation-state" : [
                   {
                       "data" : "unverified"
                   }
                   ],
                   "nh" : [
                   {
                       "selected-next-hop" : [
                       {
                           "data" : [null]
                       }
                       ],
                       "to" : [
                       {
                           "data" : "10.12.1.2"
                       }
                       ],
                       "via" : [
                       {
                           "data" : "xe-0/0/1.0"
                       }
                       ]
                   }
                   ]
               },
               {
                   "active-tag" : [
                   {
                   }
                   ],
                   "protocol-name" : [
                   {
                       "data" : "BGP"
                   }
                   ],
                   "preference" : [
                   {
                       "data" : "170"
                   }
                   ],
                   "age" : [
                   {
                       "data" : "00:01:09",
                       "attributes" : {"junos:seconds" : "69"}
                   }
                   ],
                   "local-preference" : [
                   {
                       "data" : "100"
                   }
                   ],
                   "as-path" : [
                   {
                       "data" : "65002 I"
                   }
                   ],
                   "validation-state" : [
                   {
                       "data" : "unverified"
                   }
                   ],
                   "nh" : [
                   {
                       "selected-next-hop" : [
                       {
                           "data" : [null]
                       }
                       ],
                       "to" : [
                       {
                           "data" : "10.12.2.2"
                       }
                       ],
                       "via" : [
                       {
                           "data" : "xe-0/0/2.0"
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
    """

    routes = parse_show_route_display_json(text)
    assert routes == [
        JunosMainRibRoute(
            vrf="default",
            network="192.168.123.2/32",
            protocol="BGP",
            admin=170,
            metric=None,
            next_hop_ip="10.12.1.2",
            next_hop_int="xe-0/0/1.0",
            nh_type=None,
            active=True,
        ),
        JunosMainRibRoute(
            vrf="default",
            network="192.168.123.2/32",
            protocol="BGP",
            admin=170,
            metric=None,
            next_hop_ip="10.12.2.2",
            next_hop_int="xe-0/0/2.0",
            nh_type=None,
            active=False,
        ),
    ]


def test_convert_active() -> None:
    assert convert_active("*") is True
    assert convert_active(None) is False


def test_convert_active_evpn_tags() -> None:
    # @ = routing use only (EVPN routes contribute to routing but not FIB)
    assert convert_active("@") is True
    # # = forwarding use only
    assert convert_active("#") is True


def test_parse_evpn_type5_destination() -> None:
    # Standard Type 5 with RD and /24 prefix
    assert _parse_evpn_type5_destination(
        "5:172.16.0.100:10000::0::192.168.99.0::24"
    ) == ("172.16.0.100:10000", "192.168.99.0/24")

    # Type 5 with /31 prefix
    assert _parse_evpn_type5_destination("5:172.16.0.100:10000::0::10.99.0.0::31") == (
        "172.16.0.100:10000",
        "10.99.0.0/31",
    )

    # Non-Type-5 destinations are skipped
    assert _parse_evpn_type5_destination("2:172.16.0.100:1::00::0") is None
    assert _parse_evpn_type5_destination("1:10.0.0.1:0::0011::0") is None

    # Malformed (too few :: parts)
    assert _parse_evpn_type5_destination("5:bad") is None


def test_parse_as_path_with_origin() -> None:
    # eBGP path with IGP origin
    assert _parse_as_path_with_origin("65100 65200 I") == ((65100, 65200), "I")

    # Empty path with IGP origin (locally originated)
    assert _parse_as_path_with_origin("I") == ((), "I")

    # EGP origin
    assert _parse_as_path_with_origin("65001 E") == ((65001,), "E")

    # Incomplete origin
    assert _parse_as_path_with_origin("65001 65002 ?") == ((65001, 65002), "?")

    # Empty string defaults to IGP
    assert _parse_as_path_with_origin("") == ((), "I")

    # Whitespace-only defaults to IGP
    assert _parse_as_path_with_origin("   ") == ((), "I")


def test_parse_show_route_evpn_display_json() -> None:
    """Parse EVPN Type 5 routes from real node1-1 show route output.

    Data from junos_evpn_type5 lab: node1-1 receives two EVPN routes
    via iBGP from node2-1 (route reflector). The bgp.evpn.0 table
    has two Type 5 routes with RD 172.16.0.100:10000, one with AS
    path 65100 65200 and one locally originated (empty AS path).
    The TENANT-A.evpn.0 table has the same routes but should be
    skipped (only bgp.evpn.0 is parsed to avoid double-counting).
    """
    text = """{
    "route-information" : [
    {
        "attributes" : {"xmlns" : "http://xml.juniper.net/junos/25.4R0/junos-routing"},
        "route-table" : [
        {
            "table-name" : [{ "data" : "inet.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "172.16.0.1/32" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "nh" : [{ "to" : [{ "data" : "172.16.254.9" }], "via" : [{ "data" : "ge-0/0/1.0" }] }]
                }]
            }
            ]
        },
        {
            "table-name" : [{ "data" : "bgp.evpn.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "5:172.16.0.100:10000::0::192.168.99.0::24" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "as-path" : [{ "data" : "65100 65200 I" }],
                    "nh" : [{
                        "to" : [{ "data" : "172.16.254.1" }],
                        "via" : [{ "data" : "ge-0/0/1.0" }]
                    }]
                }]
            },
            {
                "rt-destination" : [{ "data" : "5:172.16.0.100:10000::0::10.99.0.0::31" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "as-path" : [{ "data" : "I" }],
                    "nh" : [{
                        "to" : [{ "data" : "172.16.254.1" }],
                        "via" : [{ "data" : "ge-0/0/1.0" }]
                    }]
                }]
            }
            ]
        },
        {
            "table-name" : [{ "data" : "TENANT-A.evpn.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "5:172.16.0.100:10000::0::192.168.99.0::24" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "EVPN" }],
                    "preference" : [{ "data" : "170" }],
                    "nh-type" : [{ "data" : "Fictitious" }]
                }]
            }
            ]
        }
        ]
    }
    ]
}
    """

    routes = parse_show_route_evpn_display_json(text)
    assert routes == [
        JunosEvpnRoute(
            network="192.168.99.0/24",
            route_distinguisher="172.16.0.100:10000",
            vrf="default",
            protocol="BGP",
            next_hop_ip="172.16.254.1",
            next_hop_int="ge-0/0/1.0",
            active=True,
            admin=170,
            as_path=(65100, 65200),
            origin_type="I",
        ),
        JunosEvpnRoute(
            network="10.99.0.0/31",
            route_distinguisher="172.16.0.100:10000",
            vrf="default",
            protocol="BGP",
            next_hop_ip="172.16.254.1",
            next_hop_int="ge-0/0/1.0",
            active=True,
            admin=170,
            as_path=(),
            origin_type="I",
        ),
    ]


def test_parse_show_route_evpn_skips_inactive() -> None:
    """Inactive EVPN routes (e.g., backup paths) are skipped."""
    text = """{
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [{ "data" : "bgp.evpn.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "5:172.16.0.100:10000::0::10.0.0.0::24" }],
                "rt-entry" : [
                {
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "as-path" : [{ "data" : "65001 I" }],
                    "nh" : [{ "to" : [{ "data" : "10.0.0.1" }], "via" : [{ "data" : "ge-0/0/0.0" }] }]
                },
                {
                    "active-tag" : [{}],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "as-path" : [{ "data" : "65002 I" }],
                    "nh" : [{ "to" : [{ "data" : "10.0.0.2" }], "via" : [{ "data" : "ge-0/0/1.0" }] }]
                }
                ]
            }
            ]
        }
        ]
    }
    ]
}
    """
    routes = parse_show_route_evpn_display_json(text)
    assert len(routes) == 1
    assert routes[0].next_hop_ip == "10.0.0.1"


def test_parse_show_route_evpn_skips_non_type5() -> None:
    """Non-Type-5 EVPN routes (Type 2 MAC/IP) are skipped."""
    text = """{
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [{ "data" : "bgp.evpn.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "2:172.16.0.100:1::0::aa:bb:cc:00:11:22" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "as-path" : [{ "data" : "I" }],
                    "nh" : [{ "to" : [{ "data" : "10.0.0.1" }], "via" : [{ "data" : "ge-0/0/0.0" }] }]
                }]
            },
            {
                "rt-destination" : [{ "data" : "5:172.16.0.100:10000::0::10.0.0.0::24" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "as-path" : [{ "data" : "65001 I" }],
                    "nh" : [{ "to" : [{ "data" : "10.0.0.1" }], "via" : [{ "data" : "ge-0/0/0.0" }] }]
                }]
            }
            ]
        }
        ]
    }
    ]
}
    """
    routes = parse_show_route_evpn_display_json(text)
    assert len(routes) == 1
    assert routes[0].network == "10.0.0.0/24"


def test_parse_show_route_evpn_no_evpn_table() -> None:
    """Show route output with no bgp.evpn.0 table returns empty list."""
    text = """{
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [{ "data" : "inet.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "10.0.0.0/24" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "Direct" }],
                    "preference" : [{ "data" : "0" }],
                    "nh" : [{ "via" : [{ "data" : "ge-0/0/0.0" }] }]
                }]
            }
            ]
        }
        ]
    }
    ]
}
    """
    routes = parse_show_route_evpn_display_json(text)
    assert routes == []


def test_parse_show_route_evpn_locally_originated() -> None:
    """Locally originated EVPN routes (protocol=EVPN, nh-type=Fictitious)
    have no next-hop or AS path. These appear in bgp.evpn.0 on the
    originating PE (e.g., router1 in junos_evpn_type5 lab).
    """
    text = """{
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [{ "data" : "bgp.evpn.0" }],
            "rt" : [
            {
                "rt-destination" : [{ "data" : "5:172.16.0.100:10000::0::192.168.99.0::24" }],
                "rt-entry" : [{
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "EVPN" }],
                    "preference" : [{ "data" : "170" }],
                    "nh-type" : [{ "data" : "Fictitious" }]
                }]
            }
            ]
        }
        ]
    }
    ]
}
    """
    routes = parse_show_route_evpn_display_json(text)
    assert routes == [
        JunosEvpnRoute(
            network="192.168.99.0/24",
            route_distinguisher="172.16.0.100:10000",
            vrf="default",
            protocol="EVPN",
            next_hop_ip=None,
            next_hop_int=None,
            active=True,
            admin=170,
            as_path=(),
            origin_type="I",
        ),
    ]
