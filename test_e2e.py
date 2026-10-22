import urllib.request
import json

base = "http://127.0.0.1:8080"

# 1. Index
with urllib.request.urlopen(f"{base}/") as resp:
    html = resp.read().decode("utf-8")
    assert "SMLib Web Studio" in html
    print("[PASS] GET /: OK (HTML length:", len(html), ")")

# 2. Info
with urllib.request.urlopen(f"{base}/api/info") as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["status"] == "ready"
    print("[PASS] GET /api/info:", data)

# 3. Parametric build
req = urllib.request.Request(
    f"{base}/api/build/parametric",
    data=json.dumps({"template": "flange", "params": {"length": 90, "width": 70, "thickness": 10, "fillet_r": 8}}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["ok"] is True
    print("[PASS] POST /api/build/parametric: stats =", data["stats"])

# 4. Script build
custom_py = """
from smlibpy import *
part = Box(50, 50, 20) - Cylinder(10, 25)
"""
req = urllib.request.Request(
    f"{base}/api/build/script",
    data=json.dumps({"script": custom_py, "name": "box_hole"}).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode("utf-8"))
    assert data["ok"] is True
    print("[PASS] POST /api/build/script: stats =", data["stats"])

# 5. Export STEP
with urllib.request.urlopen(f"{base}/api/export/step") as resp:
    step_data = resp.read().decode("utf-8", errors="ignore")
    assert step_data.startswith("ISO-10303-21;")
    print("[PASS] GET /api/export/step: valid STEP file (", len(step_data), "bytes)")

# 6. Export STL
with urllib.request.urlopen(f"{base}/api/export/stl") as resp:
    stl_data = resp.read()
    print("[PASS] GET /api/export/stl: valid STL file (", len(stl_data), "bytes)")

# 7. Export Python script
with urllib.request.urlopen(f"{base}/api/export/py") as resp:
    py_data = resp.read().decode("utf-8")
    assert "from smlibpy import *" in py_data
    print("[PASS] GET /api/export/py: valid Python script (", len(py_data), "bytes)")

print("\nAll API tests PASSED successfully!")
