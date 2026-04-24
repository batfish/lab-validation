from lab_validation.parsers.arista.commands.bgp_routes import (
    get_weight,
    parse_show_ip_bgp_vrf_all_json,
)
from lab_validation.parsers.arista.models.routes import AristaBgpRoute


def test_parse_show_ip_bgp_vrf_all_json() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "192.168.123.4",
        "vrf": "default",
        "bgpRouteEntries":
        {"10.10.10.0/24": {
            "bgpAdvertisedPeerGroups": {},
            "maskLength": 24,
            "bgpRoutePaths": [{
                "asPathEntry": {"asPathType": null, "asPath": "1 i"},
                "med": 0,
                "localPreference": 100,
                "weight": 0,
                "reasonNotBestpath": null,
                "nextHop": "10.10.30.1",
                "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}
            }],
            "address": "10.10.10.0"},
            "10.10.20.0/24": {"bgpAdvertisedPeerGroups": {}, "maskLength": 24, "bgpRoutePaths": [{"asPathEntry": {"asPathType": null, "asPath": "i"}, "med": 0, "localPreference": 200, "weight": 0, "reasonNotBestpath": null, "nextHop": "10.10.30.2", "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}}], "address": "10.10.20.0"},
            "10.10.30.0/24": {"bgpAdvertisedPeerGroups": {}, "maskLength": 24, "bgpRoutePaths": [{"asPathEntry": {"asPathType": null, "asPath": "1 i"}, "med": 0, "localPreference": 300, "weight": 10, "reasonNotBestpath": null, "nextHop": "10.10.30.3", "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "notInstalledReason": "routeBestInactive", "valid": true, "ecmpContributor": false, "luRoute": false, "active": false, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}}], "address": "10.10.30.0"},
         "192.168.123.6/32": {"bgpAdvertisedPeerGroups": {}, "maskLength": 32, "bgpRoutePaths": [{"asPathEntry": {"asPathType": null, "asPath": "1 50 i"}, "med": 0, "localPreference": 400, "weight": 20, "reasonNotBestpath": null, "nextHop": "10.10.30.4", "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}}], "address": "192.168.123.6"}
         },
     "asn": "30"
    },
     "cust10": {"routerId": "1.1.4.10", "vrf": "cust10", "bgpRouteEntries": {
         "192.168.123.4/32": {"bgpAdvertisedPeerGroups": {}, "maskLength": 32, "bgpRoutePaths": [{"asPathEntry": {"asPathType": null, "asPath": "i"}, "med": 0, "localPreference": 0, "reasonNotBestpath": null, "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}}], "address": "192.168.123.4"}
     }, "asn": "30"},
     "cust20": {"routerId": "1.1.4.20", "vrf": "cust20", "bgpRouteEntries": {}, "asn": "30"}}}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="10.10.10.0/24",
            next_hop_ip="10.10.30.1",
            local_preference=100,
            metric=0,
            as_path=(1,),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="default",
            network="10.10.20.0/24",
            next_hop_ip="10.10.30.2",
            local_preference=200,
            metric=0,
            as_path=(),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="default",
            network="10.10.30.0/24",
            next_hop_ip="10.10.30.3",
            local_preference=300,
            metric=0,
            as_path=(1,),
            weight=10,
            is_active=False,
            is_ecmp=False,
            not_installed_reason="routeBestInactive",
            origin_protocol=None,
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="default",
            network="192.168.123.6/32",
            next_hop_ip="10.10.30.4",
            local_preference=400,
            metric=0,
            as_path=(1, 50),
            weight=20,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="cust10",
            network="192.168.123.4/32",
            next_hop_ip=None,
            local_preference=0,
            metric=0,
            as_path=(),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        ),
    ]


def test_parse_show_ip_bgp_vrf_all_json_no_metric() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "192.168.123.4",
        "vrf": "default",
        "bgpRouteEntries":
        {"10.10.10.0/24": {
            "bgpAdvertisedPeerGroups": {},
            "maskLength": 24,
            "bgpRoutePaths": [{
                "asPathEntry": {"asPathType": null, "asPath": "1 i"},
                "localPreference": 100,
                "weight": 0,
                "reasonNotBestpath": null,
                "nextHop": "10.10.30.1",
                "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}
            }],
            "address": "10.10.10.0"}
         },
     "asn": "30"
    }
    }}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="10.10.10.0/24",
            next_hop_ip="10.10.30.1",
            local_preference=100,
            metric=None,
            as_path=(1,),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        )
    ]


def test_parse_show_ip_bgp_vrf_all_json_no_local_pref() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "192.168.123.4",
        "vrf": "default",
        "bgpRouteEntries":
        {"10.10.10.0/24": {
            "bgpAdvertisedPeerGroups": {},
            "maskLength": 24,
            "bgpRoutePaths": [{
                "asPathEntry": {"asPathType": null, "asPath": "1 i"},
                "med": 0,
                "weight": 0,
                "reasonNotBestpath": null,
                "nextHop": "10.10.30.1",
                "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}
            }],
            "address": "10.10.10.0"}
         },
     "asn": "30"
    }
    }}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="10.10.10.0/24",
            next_hop_ip="10.10.30.1",
            local_preference=None,
            metric=0,
            as_path=(1,),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        )
    ]


def test_parse_show_ip_bgp_vrf_all_json_origin_incomplete() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "192.168.123.4",
        "vrf": "default",
        "bgpRouteEntries":
        {"10.10.10.0/24": {
            "bgpAdvertisedPeerGroups": {},
            "maskLength": 24,
            "bgpRoutePaths": [{
                "asPathEntry": {"asPathType": null, "asPath": "1 ?"},
                "med": 0,
                "weight": 0,
                "reasonNotBestpath": null,
                "nextHop": "10.10.30.1",
                "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}
            }],
            "address": "10.10.10.0"}
         },
     "asn": "30"
    }
    }}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="10.10.10.0/24",
            next_hop_ip="10.10.30.1",
            local_preference=None,
            metric=0,
            as_path=(1,),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="incomplete",
        )
    ]


def test_parse_bgp_local_route() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "192.168.123.4",
        "vrf": "default",
        "bgpRouteEntries":
        {"10.10.10.0/24": {
            "bgpAdvertisedPeerGroups": {},
            "maskLength": 24,
            "bgpRoutePaths": [{
                "asPathEntry": {"asPathType": null, "asPath": "1 i"},
                "med": 0,
                "weight": 0,
                "reasonNotBestpath": null,
                "nextHop": "",
                "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false}
            }],
            "address": "10.10.10.0"}
         },
     "asn": "30"
    }
    }}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="10.10.10.0/24",
            next_hop_ip=None,
            local_preference=None,
            metric=0,
            as_path=(1,),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        )
    ]


def test_parse_bgp_ecmp_routes() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "192.168.123.4",
        "vrf": "default",
        "bgpRouteEntries": {
            "192.168.255.8/32": {
              "totalPaths": 2,
              "maskLength": 32,
              "bgpRoutePaths": [
                {
                  "asPathEntry": {
                    "asPath": "1 i",
                    "asPathType": null
                  },
                  "med": 0,
                  "localPreference": 100,
                  "weight": 0,
                  "reasonNotBestpath": "noReason",
                  "nextHop": "172.31.255.0",
                  "routeType": {
                    "atomicAggregator": false,
                    "origin": "Igp",
                    "suppressed": false,
                    "sixPeRoute": false,
                    "queued": false,
                    "valid": true,
                    "ecmpContributor": true,
                    "luRoute": false,
                    "active": true,
                    "stale": false,
                    "ecmp": true,
                    "backup": false,
                    "ecmpHead": true,
                    "ucmp": false
                  }
                },
                {
                  "asPathEntry": {
                    "asPath": "1 i",
                    "asPathType": null
                  },
                  "med": 0,
                  "localPreference": 100,
                  "weight": 0,
                  "reasonNotBestpath": "noReason",
                  "nextHop": "172.31.255.2",
                  "routeType": {
                    "atomicAggregator": false,
                    "origin": "Igp",
                    "suppressed": false,
                    "sixPeRoute": false,
                    "queued": false,
                    "valid": true,
                    "ecmpContributor": true,
                    "luRoute": false,
                    "active": false,
                    "stale": false,
                    "ecmp": true,
                    "backup": false,
                    "ecmpHead": false,
                    "ucmp": false
                  }
                }
              ],
            "address": "10.10.10.0"}
         },
     "asn": "30"
    }
    }}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="192.168.255.8/32",
            next_hop_ip="172.31.255.0",
            local_preference=100,
            metric=0,
            as_path=(1,),
            weight=0,
            is_active=True,
            is_ecmp=True,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="default",
            network="192.168.255.8/32",
            next_hop_ip="172.31.255.2",
            local_preference=100,
            metric=0,
            as_path=(1,),
            weight=0,
            is_active=False,
            is_ecmp=True,
            not_installed_reason=None,
            origin_protocol=None,
            origin_type="igp",
        ),
    ]


def test_parse_show_ip_bgp_vrf_all_json_with_as_path_type() -> None:
    text = """
    {
    "vrfs":
    {"default": {
        "routerId": "1.1.1.1",
        "vrf": "default",
        "bgpRouteEntries":
        {"1.1.1.1/32": {
            "bgpAdvertisedPeerGroups": {},
            "maskLength": 32,
            "bgpRoutePaths": [{
                "asPathEntry": {"asPathType": "Local", "asPath": "i"},
                "nextHop": "",
                "peerEntry": {},
                "reasonNotBestpath": null,
                "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false, "sixPeRoute": false, "origin": "Igp"},
                "tag": 0,
                "weight": 32768
            }],
            "address": "1.1.1.1"},
            "2.2.2.2/32": {"bgpAdvertisedPeerGroups": {}, "maskLength": 32, "bgpRoutePaths": [{"asPathEntry": {"asPathType": "External", "asPath": "65002 i"}, "localPreference": 100, "med": 0, "nextHop": "10.0.0.2", "peerEntry": {}, "reasonNotBestpath": null, "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false, "sixPeRoute": false, "origin": "Igp"}, "tag": 0, "weight": 0}], "address": "2.2.2.2"},
            "3.3.3.3/32": {"bgpAdvertisedPeerGroups": {}, "maskLength": 32, "bgpRoutePaths": [{"asPathEntry": {"asPathType": "Internal", "asPath": "i"}, "localPreference": 100, "med": 0, "nextHop": "10.0.0.3", "peerEntry": {}, "reasonNotBestpath": null, "routeType": {"atomicAggregator": false, "suppressed": false, "queued": false, "valid": true, "ecmpContributor": false, "luRoute": false, "active": true, "stale": false, "ecmp": false, "backup": false, "ecmpHead": false, "ucmp": false, "sixPeRoute": false, "origin": "Igp"}, "tag": 0, "weight": 0}], "address": "3.3.3.3"}
         },
     "asn": "65001"
    }
    }}
    """
    routes = parse_show_ip_bgp_vrf_all_json(text)
    assert routes == [
        AristaBgpRoute(
            vrf="default",
            network="1.1.1.1/32",
            next_hop_ip=None,
            local_preference=None,
            metric=None,
            as_path=(),
            weight=32768,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol="bgp",
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="default",
            network="2.2.2.2/32",
            next_hop_ip="10.0.0.2",
            local_preference=100,
            metric=0,
            as_path=(65002,),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol="bgp",
            origin_type="igp",
        ),
        AristaBgpRoute(
            vrf="default",
            network="3.3.3.3/32",
            next_hop_ip="10.0.0.3",
            local_preference=100,
            metric=0,
            as_path=(),
            weight=0,
            is_active=True,
            is_ecmp=False,
            not_installed_reason=None,
            origin_protocol="ibgp",
            origin_type="igp",
        ),
    ]


def test_get_weight() -> None:
    weight = None
    nhip = None
    assert get_weight(weight, nhip) == 0

    weight = 123
    nhip = "1.2.3.4"
    assert get_weight(weight, nhip) == 123
