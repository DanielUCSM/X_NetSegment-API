from ipaddress import IPv4Network

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
FLSM = "/api/v1/subnetting/flsm"
VLSM = "/api/v1/subnetting/vlsm"
AGGREGATE = "/api/v1/supernetting/aggregate"


def test_health_and_documentation():
    assert client.get("/health").json() == {"status": "ok", "version": "1.0.0"}
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["version"] == "1.0.0"


@pytest.mark.parametrize("requested,count,prefix", [(1, 1, 24), (3, 4, 26), (4, 4, 26)])
def test_flsm_partitions_entire_network(requested, count, prefix):
    response = client.post(FLSM, json={"network": "192.168.10.0/24", "subnets_needed": requested})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["allocated_subnets_count"] == count
    assert data["cidr_prefix"] == prefix
    networks = [IPv4Network(row["network_address"] + row["cidr"]) for row in data["subnets"]]
    assert sum(network.num_addresses for network in networks) == 256
    assert networks[0].network_address.exploded == "192.168.10.0"
    assert networks[-1].broadcast_address.exploded == "192.168.10.255"
    assert all(not first.overlaps(second) for index, first in enumerate(networks) for second in networks[index + 1:])


def test_flsm_30_has_two_usable_hosts():
    data = client.post(FLSM, json={"network": "10.0.0.0/30", "subnets_needed": 1}).json()["data"]
    assert data["usable_hosts_per_subnet"] == 2
    assert data["subnets"][0]["first_usable_ip"] == "10.0.0.1"
    assert data["subnets"][0]["last_usable_ip"] == "10.0.0.2"


@pytest.mark.parametrize("network,count", [("10.0.0.0/30", 2), ("10.0.0.0/31", 1), ("10.0.0.1/32", 1)])
def test_flsm_rejects_blocks_without_conventional_hosts(network, count):
    assert client.post(FLSM, json={"network": network, "subnets_needed": count}).status_code == 400


def test_vlsm_dossier_and_unused_space():
    response = client.post(VLSM, json={"base_network": "172.16.0.0/22", "departments": [
        {"name": "Ventas", "hosts_needed": 120},
        {"name": "Ingenieria", "hosts_needed": 500},
        {"name": "Servidores", "hosts_needed": 50},
        {"name": "Enlace-WAN", "hosts_needed": 2},
    ]})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_space_allocated"] == 708
    assert data["total_space_remaining"] == 316
    assert data["total_host_capacity_unused"] == 28
    rows = data["allocations"]
    assert [row["department"] for row in rows] == ["Ingenieria", "Ventas", "Servidores", "Enlace-WAN"]
    assert [row["network_address"] + row["cidr"] for row in rows] == [
        "172.16.0.0/23", "172.16.2.0/25", "172.16.2.128/26", "172.16.2.192/30",
    ]


@pytest.mark.parametrize("hosts,prefix", [(1, "/30"), (2, "/30"), (3, "/29"), (6, "/29"), (7, "/28"), (254, "/24")])
def test_vlsm_host_boundaries(hosts, prefix):
    response = client.post(VLSM, json={"base_network": "10.0.0.0/24", "departments": [{"name": "A", "hosts_needed": hosts}]})
    assert response.status_code == 200
    assert response.json()["data"]["allocations"][0]["cidr"] == prefix


def test_vlsm_capacity_is_atomic():
    response = client.post(VLSM, json={"base_network": "10.0.0.0/24", "departments": [
        {"name": "A", "hosts_needed": 200}, {"name": "B", "hosts_needed": 100},
    ]})
    assert response.status_code == 400
    assert response.json()["error_code"] == "NETWORK_CAPACITY_EXCEEDED"
    assert "data" not in response.json()


def test_aggregate_exact_route_and_unsorted_inputs():
    response = client.post(AGGREGATE, json={"networks": ["192.168.2.0/24", "192.168.0.0/24", "192.168.3.0/24", "192.168.1.0/24"]})
    assert response.status_code == 200
    assert response.json()["data"]["summary_route"] == "192.168.0.0/22"
    assert response.json()["data"]["routing_table_reduction"] == "75.0%"


@pytest.mark.parametrize("networks,code", [
    (["10.0.0.0/24", "10.0.2.0/24"], "NETWORKS_NOT_CONTIGUOUS"),
    (["10.0.1.0/24", "10.0.2.0/24"], "INVALID_CIDR_AGGREGATION"),
    (["10.0.0.0/24", "10.0.0.0/24"], "OVERLAPPING_NETWORKS"),
    (["10.0.0.0/24", "10.0.0.0/25"], "OVERLAPPING_NETWORKS"),
])
def test_aggregate_does_not_add_addresses(networks, code):
    response = client.post(AGGREGATE, json={"networks": networks})
    assert response.status_code == 400
    assert response.json()["error_code"] == code


def test_aggregate_single_and_mixed_prefixes():
    assert client.post(AGGREGATE, json={"networks": ["10.0.0.1/32"]}).json()["data"]["summary_route"] == "10.0.0.1/32"
    assert client.post(AGGREGATE, json={"networks": ["10.0.0.0/25", "10.0.0.128/26", "10.0.0.192/26"]}).json()["data"]["summary_route"] == "10.0.0.0/24"


@pytest.mark.parametrize("body", [
    {"network": "192.168.1.300/24", "subnets_needed": 4},
    {"network": "192.168.1.1/24", "subnets_needed": 4},
    {"network": "2001:db8::/64", "subnets_needed": 4},
    {"network": "192.168.1.0/255.255.255.0", "subnets_needed": 4},
    {"network": "192.168.1.0/24", "subnets_needed": True},
    {"network": "192.168.1.0/24", "subnets_needed": "4"},
    {"network": "192.168.1.0/24", "subnets_needed": 0},
    {"network": "192.168.1.0/24", "subnets_needed": 4097},
    {"network": "192.168.1.0/24", "subnets_needed": 4, "extra": 1},
])
def test_flsm_validation(body):
    assert client.post(FLSM, json=body).status_code == 422


@pytest.mark.parametrize("departments", [[], [{"name": " ", "hosts_needed": 2}],
    [{"name": "A", "hosts_needed": 0}], [{"name": "A", "hosts_needed": True}],
    [{"name": "A", "hosts_needed": 2}, {"name": "a", "hosts_needed": 3}],
])
def test_vlsm_validation(departments):
    assert client.post(VLSM, json={"base_network": "10.0.0.0/24", "departments": departments}).status_code == 422


def test_invalid_json_empty_aggregate_and_missing_endpoint():
    assert client.post(FLSM, content="{", headers={"Content-Type": "application/json"}).status_code == 422
    assert client.post(AGGREGATE, json={"networks": []}).status_code == 422
    assert client.get("/missing").status_code == 404
