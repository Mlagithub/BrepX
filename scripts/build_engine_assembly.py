"""Construct a complete, visually recognizable 2.0L I4 automotive engine assembly.

Components:
1. Cylinder Block with 4 distinct combustion chambers (bores)
2. Cylinder Head & Valve/Cam Cover on top
3. Oil Pan / Sump attached to bottom
4. Front Crankshaft Drive Pulley
5. Rear Transmission Flywheel disc
"""

from __future__ import annotations

import json
import urllib.request

BASE_URL = "http://127.0.0.1:8080/api"


def post_cmd(cmd: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE_URL}/command",
        data=json.dumps(cmd).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


def main() -> None:
    print("=== Building Real 2.0L I4 Engine Assembly ===")

    # 1. Main Engine Block (420 x 220 x 210)
    print("\n1. Generating Engine Block...")
    c1 = post_cmd({
        "command_id": "c1_block",
        "op": "box",
        "params": {"length": 420.0, "width": 220.0, "height": 210.0},
        "idempotency_key": "k_engine_block",
    })
    print(f"Block created (v{c1['version']})")

    # 2. Cylinder Head & Valve Cover on Top (420 x 190 x 90)
    print("\n2. Generating Cylinder Head & Valve Cover on top...")
    c2 = post_cmd({
        "command_id": "c2_head",
        "op": "box",
        "params": {"length": 420.0, "width": 190.0, "height": 90.0},
        "idempotency_key": "k_engine_head",
    })
    print(f"Head created (v{c2['version']})")

    # Move head to sit right on top of the block: Z shift = (210/2) + (90/2) = 150
    post_cmd({
        "command_id": "c2_head_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_2']"},
        "params": {"dx": 0.0, "dy": 0.0, "dz": 150.0},
        "idempotency_key": "k_engine_head_move",
    })
    print("Head translated to top deck.")

    # 3. Oil Pan / Sump below Block (380 x 180 x 80)
    print("\n3. Generating Oil Pan / Sump below block...")
    c3 = post_cmd({
        "command_id": "c3_oilpan",
        "op": "box",
        "params": {"length": 380.0, "width": 180.0, "height": 80.0},
        "idempotency_key": "k_engine_oilpan",
    })
    print(f"Oil pan created (v{c3['version']})")

    # Move oil pan to bottom: Z shift = -((210/2) + (80/2)) = -145
    post_cmd({
        "command_id": "c3_oilpan_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_3']"},
        "params": {"dx": -10.0, "dy": 0.0, "dz": -145.0},
        "idempotency_key": "k_engine_oilpan_move",
    })
    print("Oil pan translated to crankcase bottom.")

    # 4. Front Drive Belt Pulley (Cylinder at X = +230, radius 65, height 35)
    print("\n4. Generating Front Crankshaft Belt Pulley...")
    c4 = post_cmd({
        "command_id": "c4_pulley",
        "op": "cylinder",
        "params": {"radius": 65.0, "height": 35.0},
        "idempotency_key": "k_engine_pulley",
    })
    print(f"Pulley created (v{c4['version']})")

    # Rotate pulley to align with crank axis (rotate 90 deg around Y axis so cylinder axis is X)
    post_cmd({
        "command_id": "c4_pulley_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_4']"},
        "params": {"axis": "Y", "angle": 90.0},
        "idempotency_key": "k_engine_pulley_rot",
    })

    # Move pulley to front crank snout: X = +210 + (35/2) = 227.5, Z = -60 (lower crank center)
    post_cmd({
        "command_id": "c4_pulley_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_4']"},
        "params": {"dx": 227.5, "dy": 0.0, "dz": -60.0},
        "idempotency_key": "k_engine_pulley_move",
    })
    print("Pulley positioned at front crankshaft snout.")

    # 5. Rear Transmission Flywheel Disc (Cylinder at X = -225, radius 135, height 25)
    print("\n5. Generating Rear Transmission Flywheel...")
    c5 = post_cmd({
        "command_id": "c5_flywheel",
        "op": "cylinder",
        "params": {"radius": 135.0, "height": 25.0},
        "idempotency_key": "k_engine_flywheel",
    })
    print(f"Flywheel created (v{c5['version']})")

    # Rotate flywheel axis to X
    post_cmd({
        "command_id": "c5_flywheel_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_5']"},
        "params": {"axis": "Y", "angle": 90.0},
        "idempotency_key": "k_engine_flywheel_rot",
    })

    # Move flywheel to rear crank output: X = -(210 + 12.5) = -222.5, Z = -60
    post_cmd({
        "command_id": "c5_flywheel_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_5']"},
        "params": {"dx": -222.5, "dy": 0.0, "dz": -60.0},
        "idempotency_key": "k_engine_flywheel_move",
    })
    print("Flywheel positioned at rear transmission interface.")

    # 6. Intake Manifold (Box on the side, Y = +140, 360 x 70 x 70)
    print("\n6. Generating Intake Manifold Plenum...")
    c6 = post_cmd({
        "command_id": "c6_intake",
        "op": "box",
        "params": {"length": 360.0, "width": 70.0, "height": 70.0},
        "idempotency_key": "k_engine_intake",
    })
    print(f"Intake plenum created (v{c6['version']})")

    post_cmd({
        "command_id": "c6_intake_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_6']"},
        "params": {"dx": 0.0, "dy": 135.0, "dz": 100.0},
        "idempotency_key": "k_engine_intake_move",
    })
    print("Intake manifold positioned on intake side.")

    print("\n=== Engine Assembly Complete! ===")


if __name__ == "__main__":
    main()
