from lab_validation.parsers.junos.commands.routes import (
    convert_active,
    parse_show_route_display_json,
)
from lab_validation.parsers.junos.models.routes import JunosMainRibRoute


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
    active_tag = "*"
    result = convert_active(active_tag)
    assert result is True

    active_tag = None
    result = convert_active(active_tag)
    assert result is False
