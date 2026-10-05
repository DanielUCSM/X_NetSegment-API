import json
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
root = Path(__file__).resolve().parents[1]


def call(path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    request = Request(base + path, data=data, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=10) as response:
            return response.status, json.load(response)
    except HTTPError as error:
        return error.code, json.load(error)


code, health = call("/health")
assert code == 200 and health["status"] == "ok", (code, health)
print("PASS health")
for filename, path, expected in [
    ("flsm.json", "/api/v1/subnetting/flsm", ("cidr_prefix", 26)),
    ("vlsm.json", "/api/v1/subnetting/vlsm", ("total_space_allocated", 708)),
    ("aggregate.json", "/api/v1/supernetting/aggregate", ("summary_route", "192.168.0.0/22")),
]:
    payload = json.loads((root / "examples" / filename).read_text())
    code, body = call(path, payload)
    key, value = expected
    assert code == 200 and body["data"][key] == value, (code, body)
    print(f"PASS {filename}")
code, _ = call("/api/v1/subnetting/flsm", {"network": "192.168.1.300/24", "subnets_needed": 4})
assert code == 422, code
print("PASS invalid IPv4 -> 422")
code, _ = call("/api/v1/subnetting/vlsm", {"base_network": "10.0.0.0/24", "departments": [{"name": "A", "hosts_needed": 500}]})
assert code == 400, code
print("PASS insufficient capacity -> 400")
print("6 comprobaciones HTTP correctas")
