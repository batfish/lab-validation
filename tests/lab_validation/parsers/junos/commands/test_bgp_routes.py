from lab_validation.parsers.junos.commands.bgp_routes import (
    _get_as_path,
    convert_active,
    parse_show_route_protocol_bgp_display_json,
)
from lab_validation.parsers.junos.models.routes import JunosBgpRoute


def test_parse_show_route_protocol_bgp_display_json() -> None:
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
                "data" : "15"
            }
            ],
            "total-route-count" : [
            {
                "data" : "16"
            }
            ],
            "active-route-count" : [
            {
                "data" : "15"
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
                    "age" : [
                    {
                        "data" : "1d 03:16:30",
                        "attributes" : {"junos:seconds" : "98190"}
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
                    "data" : "10.10.20.0/24"
                }
                ],
                "rt-entry" : [
                {
                    "active-tag" : [
                    {
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
                        "data" : "1d 03:16:30",
                        "attributes" : {"junos:seconds" : "98190"}
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
                        "data" : "I"
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
                            "data" : "10.10.50.2"
                        }
                        ],
                        "via" : [
                        {
                            "data" : "xe-0/0/1.0"
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
            "destination-count" : [
            {
                "data" : "1"
            }
            ],
            "total-route-count" : [
            {
                "data" : "1"
            }
            ],
            "active-route-count" : [
            {
                "data" : "1"
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
            ]
        },
        {
            "table-name" : [
            {
                "data" : "cust20.inet.0"
            }
            ],
            "destination-count" : [
            {
                "data" : "1"
            }
            ],
            "total-route-count" : [
            {
                "data" : "1"
            }
            ],
            "active-route-count" : [
            {
                "data" : "1"
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
            ]
        }
        ]
    }
    ]
}

{master:0}
    """
    routes = parse_show_route_protocol_bgp_display_json(text)
    assert routes == [
        JunosBgpRoute(
            network="10.10.10.0/24",
            vrf="default",
            preference=170,
            origin_protocol="BGP",
            next_hop_ip="10.10.50.1",
            next_hop_int="xe-0/0/0.0",
            metric=0,
            local_preference=100,
            as_path=(1,),
            origin_type="I",
            is_active=True,
        ),
        JunosBgpRoute(
            network="10.10.20.0/24",
            vrf="default",
            preference=170,
            next_hop_ip="10.10.50.2",
            next_hop_int="xe-0/0/1.0",
            origin_protocol="BGP",
            metric=0,
            local_preference=100,
            as_path=(),
            origin_type="I",
            is_active=False,
        ),
    ]


def test_parse_show_route_protocol_bgp_detail_with_communities() -> None:
    # `show route protocol bgp detail | display json` differs from the brief
    # form in three places this test covers:
    #   1. rt-destination is bare ("10.10.10.0") and rt-prefix-length is its
    #      own field instead of the "10.10.10.0/24" combined string.
    #   2. as-path data is prefixed with "AS path: ".
    #   3. The communities array is present.
    text = """
    {
    "route-information" : [
    {
        "attributes" : {"xmlns" : "http://xml.juniper.net/junos/25.4R0/junos-routing"},
        "route-table" : [
        {
            "table-name" : [{"data" : "inet.0"}],
            "rt" : [
            {
                "attributes" : {"junos:style" : "detail"},
                "rt-destination" : [{"data" : "10.10.10.0"}],
                "rt-prefix-length" : [{"data" : "24"}],
                "rt-entry" : [
                {
                    "active-tag" : [{"data" : "*"}],
                    "protocol-name" : [{"data" : "BGP"}],
                    "preference" : [{"data" : "170"}],
                    "med" : [{"data" : "0"}],
                    "local-preference" : [{"data" : "100"}],
                    "as-path" : [{"data" : "AS path: 1 I"}],
                    "communities" : [
                    {
                        "community" : [
                            {"data" : "65001:100"},
                            {"data" : "target:65001:200"},
                            {"data" : "no-export"}
                        ]
                    }
                    ],
                    "nh" : [
                    {
                        "to" : [{"data" : "10.10.50.1"}],
                        "via" : [{"data" : "xe-0/0/0.0"}]
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
    routes = parse_show_route_protocol_bgp_display_json(text)
    assert routes == [
        JunosBgpRoute(
            network="10.10.10.0/24",
            vrf="default",
            preference=170,
            origin_protocol="BGP",
            next_hop_ip="10.10.50.1",
            next_hop_int="xe-0/0/0.0",
            metric=0,
            local_preference=100,
            as_path=(1,),
            origin_type="I",
            is_active=True,
            communities=("65001:100", "target:65001:200", "no-export"),
        ),
    ]


def test_parse_nhh_discard_route() -> None:
    """Routes with next-hop discard/reject have nhh instead of nh."""
    text = """
    {
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [{ "data" : "inet.0" }],
            "destination-count" : [{ "data" : "1" }],
            "total-route-count" : [{ "data" : "1" }],
            "active-route-count" : [{ "data" : "1" }],
            "holddown-route-count" : [{ "data" : "0" }],
            "hidden-route-count" : [{ "data" : "0" }],
            "rt" : [
            {
                "attributes" : {"junos:style" : "detail"},
                "rt-destination" : [{ "data" : "10.50.21.0" }],
                "rt-prefix-length" : [{ "data" : "24" }],
                "rt-entry-count" : [{ "data" : "1", "attributes" : {"junos:format" : "1 entry"} }],
                "rt-entry" : [
                {
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "local-preference" : [{ "data" : "100" }],
                    "as-path" : [{ "data" : "AS path: 65001 I" }],
                    "nhh" : [
                    {
                        "attributes" : {"junos:indent" : "16"},
                        "nh-type" : [{ "data" : "Discard" }],
                        "nh-index" : [{ "data" : "0" }],
                        "nh-address" : [{ "data" : "0x91b9114" }],
                        "nh-reference-count" : [{ "data" : "2" }],
                        "nh-kernel-id" : [{ "data" : "0" }]
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
    routes = parse_show_route_protocol_bgp_display_json(text)
    assert len(routes) == 1
    r = routes[0]
    assert r.network == "10.50.21.0/24"
    assert r.next_hop_ip == "discard"
    assert r.next_hop_int == "discard"
    assert r.as_path == (65001,)
    assert r.is_active is True


def test_parse_metric_from_detail_form() -> None:
    """`show route protocol bgp detail | display json` puts MED in the
    `metric` key. The brief form puts it in `med`. Parser must read both."""
    text = """
    {
    "route-information" : [
    {
        "route-table" : [
        {
            "table-name" : [{ "data" : "inet.0" }],
            "destination-count" : [{ "data" : "1" }],
            "total-route-count" : [{ "data" : "1" }],
            "active-route-count" : [{ "data" : "1" }],
            "holddown-route-count" : [{ "data" : "0" }],
            "hidden-route-count" : [{ "data" : "0" }],
            "rt" : [
            {
                "attributes" : {"junos:style" : "detail"},
                "rt-destination" : [{ "data" : "10.50.61.0" }],
                "rt-prefix-length" : [{ "data" : "24" }],
                "rt-entry-count" : [{ "data" : "1", "attributes" : {"junos:format" : "1 entry"} }],
                "rt-entry" : [
                {
                    "active-tag" : [{ "data" : "*" }],
                    "protocol-name" : [{ "data" : "BGP" }],
                    "preference" : [{ "data" : "170" }],
                    "metric" : [{ "data" : "200" }],
                    "local-preference" : [{ "data" : "100" }],
                    "as-path" : [{ "data" : "AS path: 65001 I" }],
                    "nh" : [
                    {
                        "to" : [{ "data" : "10.0.12.0" }],
                        "via" : [{ "data" : "ge-0/0/0.0" }]
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
    routes = parse_show_route_protocol_bgp_display_json(text)
    assert len(routes) == 1
    assert routes[0].metric == 200


def test_get_as_path() -> None:
    assert _get_as_path("I") == ((), "I")
    assert _get_as_path("1 2 I") == ((1, 2), "I")
    assert _get_as_path("1 2 E") == ((1, 2), "E")
    assert _get_as_path("1 2 ?") == ((1, 2), "?")
    # `detail | display json` prefixes the AS path with "AS path: ".
    assert _get_as_path("AS path: 65001 I") == ((65001,), "I")
    assert _get_as_path("AS path: I") == ((), "I")


def test_convert_active() -> None:
    active_tag = "*"
    result = convert_active(active_tag)
    assert result is True

    active_tag = None
    result = convert_active(active_tag)
    assert result is False
