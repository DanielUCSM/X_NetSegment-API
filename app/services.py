from ipaddress import IPv4Address, IPv4Network, collapse_addresses

from app.schemas import AggregateRequest, FLSMRequest, VLSMRequest


class NetworkError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message


def subnet_data(network):
    return {
        "network_address": str(network.network_address),
        "cidr": f"/{network.prefixlen}",
        "netmask": str(network.netmask),
        "wildcard_mask": str(network.hostmask),
        "first_usable_ip": str(network.network_address + 1),
        "last_usable_ip": str(network.broadcast_address - 1),
        "broadcast_address": str(network.broadcast_address),
    }


def calculate_flsm(request: FLSMRequest):
    bits = (request.subnets_needed - 1).bit_length()
    prefix = request.network.prefixlen + bits
    if prefix > 30:
        raise NetworkError(
            "NETWORK_CAPACITY_EXCEEDED",
            "La division no permite subredes convencionales con red, broadcast y hosts.",
        )
    subnets = list(request.network.subnets(new_prefix=prefix))
    return {
        "base_network": str(request.network),
        "requested_subnets_count": request.subnets_needed,
        "allocated_subnets_count": len(subnets),
        "subnet_mask": str(subnets[0].netmask),
        "cidr_prefix": prefix,
        "total_hosts_per_subnet": subnets[0].num_addresses,
        "usable_hosts_per_subnet": subnets[0].num_addresses - 2,
        "subnets": [
            {"subnet_id": index, **subnet_data(network)}
            for index, network in enumerate(subnets, start=1)
        ],
    }


def calculate_vlsm(request: VLSMRequest):
    departments = sorted(request.departments, key=lambda item: item.hosts_needed, reverse=True)
    blocks = [1 << (item.hosts_needed + 1).bit_length() for item in departments]
    allocated = sum(blocks)
    if allocated > request.base_network.num_addresses:
        raise NetworkError(
            "NETWORK_CAPACITY_EXCEEDED",
            "La demanda supera la capacidad del bloque IPv4.",
        )
    cursor = int(request.base_network.network_address)
    allocations = []
    for department, block in zip(departments, blocks):
        prefix = 32 - (block.bit_length() - 1)
        network = IPv4Network((IPv4Address(cursor), prefix), strict=True)
        allocations.append({
            "department": department.name,
            "requested_hosts": department.hosts_needed,
            "allocated_hosts": block - 2,
            **subnet_data(network),
        })
        cursor += block
    requested_hosts = sum(item.hosts_needed for item in departments)
    return {
        "base_network": str(request.base_network),
        "total_space_available": request.base_network.num_addresses,
        "total_space_allocated": allocated,
        "total_space_remaining": request.base_network.num_addresses - allocated,
        "total_requested_hosts": requested_hosts,
        "total_host_capacity_unused": allocated - 2 * len(allocations) - requested_hosts,
        "allocations": allocations,
    }


def aggregate_networks(request: AggregateRequest):
    networks = sorted(request.networks, key=lambda item: int(item.network_address))
    for previous, current in zip(networks, networks[1:]):
        if current.network_address <= previous.broadcast_address:
            raise NetworkError("OVERLAPPING_NETWORKS", "Las redes se duplican o se solapan.")
        if int(current.network_address) != int(previous.broadcast_address) + 1:
            raise NetworkError("NETWORKS_NOT_CONTIGUOUS", "Las redes no son contiguas.")
    collapsed = list(collapse_addresses(networks))
    if len(collapsed) != 1:
        raise NetworkError(
            "INVALID_CIDR_AGGREGATION",
            "Las redes no forman una unica superred CIDR exacta y alineada.",
        )
    network = collapsed[0]
    return {
        "input_networks_count": len(networks),
        "summary_route": str(network),
        "summary_netmask": str(network.netmask),
        "summary_wildcard": str(network.hostmask),
        "range_covered": {
            "start_address": str(network.network_address),
            "end_address": str(network.broadcast_address),
        },
        "routing_table_reduction": f"{(1 - 1 / len(networks)) * 100:.1f}%",
    }
