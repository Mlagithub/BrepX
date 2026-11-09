"""Construct complete 2025 Merida SCULTURA ENDURANCE 6000 bicycle assembly."""

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
    print("=== Building 2025 Merida SCULTURA ENDURANCE 6000 Assembly ===")

    # 1. BB Shell (Cylinder at [0,0,0], r=22, h=68 along Y)
    print("\n1. BB Shell...")
    c1 = post_cmd({
        "command_id": "c1_bb",
        "op": "cylinder",
        "params": {"radius": 22.0, "height": 68.0},
        "idempotency_key": "k_bike_bb",
    })
    post_cmd({
        "command_id": "c1_bb_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_1']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_bb_rot",
    })

    # 2. Down Tube (Box/Cylinder diagonal from [0,0,0] to [430, 0, 410])
    print("\n2. Down Tube...")
    c2 = post_cmd({
        "command_id": "c2_dt",
        "op": "box",
        "params": {"length": 594.0, "width": 48.0, "height": 48.0},
        "idempotency_key": "k_bike_dt",
    })
    post_cmd({
        "command_id": "c2_dt_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_2']"},
        "params": {"axis": "Y", "angle": -43.6},
        "idempotency_key": "k_bike_dt_rot",
    })
    post_cmd({
        "command_id": "c2_dt_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_2']"},
        "params": {"dx": 215.0, "dy": 0.0, "dz": 205.0},
        "idempotency_key": "k_bike_dt_move",
    })

    # 3. Seat Tube (Diagonal from [0,0,0] to [-140, 0, 460])
    print("\n3. Seat Tube...")
    c3 = post_cmd({
        "command_id": "c3_st",
        "op": "cylinder",
        "params": {"radius": 18.0, "height": 481.0},
        "idempotency_key": "k_bike_st",
    })
    post_cmd({
        "command_id": "c3_st_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_3']"},
        "params": {"axis": "Y", "angle": 16.5},
        "idempotency_key": "k_bike_st_rot",
    })
    post_cmd({
        "command_id": "c3_st_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_3']"},
        "params": {"dx": -70.0, "dy": 0.0, "dz": 230.0},
        "idempotency_key": "k_bike_st_move",
    })

    # 4. Top Tube (From [380, 0, 584] to [-140, 0, 460])
    print("\n4. Top Tube...")
    c4 = post_cmd({
        "command_id": "c4_tt",
        "op": "box",
        "params": {"length": 535.0, "width": 36.0, "height": 36.0},
        "idempotency_key": "k_bike_tt",
    })
    post_cmd({
        "command_id": "c4_tt_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_4']"},
        "params": {"axis": "Y", "angle": 13.4},
        "idempotency_key": "k_bike_tt_rot",
    })
    post_cmd({
        "command_id": "c4_tt_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_4']"},
        "params": {"dx": 120.0, "dy": 0.0, "dz": 522.0},
        "idempotency_key": "k_bike_tt_move",
    })

    # 5. Head Tube (From [430, 0, 410] to [380, 0, 584])
    print("\n5. Head Tube...")
    c5 = post_cmd({
        "command_id": "c5_ht",
        "op": "cylinder",
        "params": {"radius": 26.0, "height": 181.0},
        "idempotency_key": "k_bike_ht",
    })
    post_cmd({
        "command_id": "c5_ht_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_5']"},
        "params": {"axis": "Y", "angle": -16.0},
        "idempotency_key": "k_bike_ht_rot",
    })
    post_cmd({
        "command_id": "c5_ht_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_5']"},
        "params": {"dx": 405.0, "dy": 0.0, "dz": 497.0},
        "idempotency_key": "k_bike_ht_move",
    })

    # 6. Fork Legs (From headtube bottom [430, 0, 410] to front dropout [587, 0, 70])
    print("\n6. Carbon Fork Legs...")
    c6_l = post_cmd({
        "command_id": "c6_fork_l",
        "op": "box",
        "params": {"length": 375.0, "width": 24.0, "height": 38.0},
        "idempotency_key": "k_bike_fork_l",
    })
    post_cmd({
        "command_id": "c6_fork_l_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_6']"},
        "params": {"axis": "Y", "angle": -24.7},
        "idempotency_key": "k_bike_fork_l_rot",
    })
    post_cmd({
        "command_id": "c6_fork_l_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_6']"},
        "params": {"dx": 508.5, "dy": 50.0, "dz": 240.0},
        "idempotency_key": "k_bike_fork_l_move",
    })

    c6_r = post_cmd({
        "command_id": "c6_fork_r",
        "op": "box",
        "params": {"length": 375.0, "width": 24.0, "height": 38.0},
        "idempotency_key": "k_bike_fork_r",
    })
    post_cmd({
        "command_id": "c6_fork_r_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_7']"},
        "params": {"axis": "Y", "angle": -24.7},
        "idempotency_key": "k_bike_fork_r_rot",
    })
    post_cmd({
        "command_id": "c6_fork_r_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_7']"},
        "params": {"dx": 508.5, "dy": -50.0, "dz": 240.0},
        "idempotency_key": "k_bike_fork_r_move",
    })

    # 7. Chainstays (From [0,0,0] to [-418, 0, 70])
    print("\n7. Chainstays...")
    c7_l = post_cmd({
        "command_id": "c7_cs_l",
        "op": "box",
        "params": {"length": 424.0, "width": 20.0, "height": 30.0},
        "idempotency_key": "k_bike_cs_l",
    })
    post_cmd({
        "command_id": "c7_cs_l_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_8']"},
        "params": {"axis": "Y", "angle": 9.5},
        "idempotency_key": "k_bike_cs_l_rot",
    })
    post_cmd({
        "command_id": "c7_cs_l_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_8']"},
        "params": {"dx": -209.0, "dy": 68.0, "dz": 35.0},
        "idempotency_key": "k_bike_cs_l_move",
    })

    c7_r = post_cmd({
        "command_id": "c7_cs_r",
        "op": "box",
        "params": {"length": 424.0, "width": 20.0, "height": 30.0},
        "idempotency_key": "k_bike_cs_r",
    })
    post_cmd({
        "command_id": "c7_cs_r_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_9']"},
        "params": {"axis": "Y", "angle": 9.5},
        "idempotency_key": "k_bike_cs_r_rot",
    })
    post_cmd({
        "command_id": "c7_cs_r_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_9']"},
        "params": {"dx": -209.0, "dy": -68.0, "dz": 35.0},
        "idempotency_key": "k_bike_cs_r_move",
    })

    # 8. Seatstays (From [-418, 0, 70] to [-140, 0, 460])
    print("\n8. Seatstays...")
    c8_l = post_cmd({
        "command_id": "c8_ss_l",
        "op": "cylinder",
        "params": {"radius": 10.0, "height": 479.0},
        "idempotency_key": "k_bike_ss_l",
    })
    post_cmd({
        "command_id": "c8_ss_l_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_10']"},
        "params": {"axis": "Y", "angle": 35.5},
        "idempotency_key": "k_bike_ss_l_rot",
    })
    post_cmd({
        "command_id": "c8_ss_l_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_10']"},
        "params": {"dx": -279.0, "dy": 45.0, "dz": 265.0},
        "idempotency_key": "k_bike_ss_l_move",
    })

    c8_r = post_cmd({
        "command_id": "c8_ss_r",
        "op": "cylinder",
        "params": {"radius": 10.0, "height": 479.0},
        "idempotency_key": "k_bike_ss_r",
    })
    post_cmd({
        "command_id": "c8_ss_r_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_11']"},
        "params": {"axis": "Y", "angle": 35.5},
        "idempotency_key": "k_bike_ss_r_rot",
    })
    post_cmd({
        "command_id": "c8_ss_r_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_11']"},
        "params": {"dx": -279.0, "dy": -45.0, "dz": 265.0},
        "idempotency_key": "k_bike_ss_r_move",
    })

    # 9. 700x32C Wheelsets (Torus at front [+587, 0, 70] and rear [-418, 0, 70])
    print("\n9. Front & Rear 700x32C Wheelsets...")
    c9_f = post_cmd({
        "command_id": "c9_wheel_f",
        "op": "torus",
        "params": {"radius_major": 326.0, "radius_minor": 16.0},
        "idempotency_key": "k_bike_wheel_f",
    })
    post_cmd({
        "command_id": "c9_wheel_f_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_12']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_wheel_f_rot",
    })
    post_cmd({
        "command_id": "c9_wheel_f_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_12']"},
        "params": {"dx": 587.0, "dy": 0.0, "dz": 70.0},
        "idempotency_key": "k_bike_wheel_f_move",
    })

    c9_r = post_cmd({
        "command_id": "c9_wheel_r",
        "op": "torus",
        "params": {"radius_major": 326.0, "radius_minor": 16.0},
        "idempotency_key": "k_bike_wheel_r",
    })
    post_cmd({
        "command_id": "c9_wheel_r_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_13']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_wheel_r_rot",
    })
    post_cmd({
        "command_id": "c9_wheel_r_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_13']"},
        "params": {"dx": -418.0, "dy": 0.0, "dz": 70.0},
        "idempotency_key": "k_bike_wheel_r_move",
    })

    # 10. Drivetrain: Shimano 105 50-34T Chainrings & Cranks
    print("\n10. Shimano 105 Chainrings & Cranks...")
    c10_cr = post_cmd({
        "command_id": "c10_chainring",
        "op": "cylinder",
        "params": {"radius": 105.0, "height": 6.0},
        "idempotency_key": "k_bike_chainring",
    })
    post_cmd({
        "command_id": "c10_chainring_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_14']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_chainring_rot",
    })
    post_cmd({
        "command_id": "c10_chainring_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_14']"},
        "params": {"dx": 0.0, "dy": 50.0, "dz": 0.0},
        "idempotency_key": "k_bike_chainring_move",
    })

    # Crank R
    c10_ck_r = post_cmd({
        "command_id": "c10_crank_r",
        "op": "box",
        "params": {"length": 172.5, "width": 14.0, "height": 32.0},
        "idempotency_key": "k_bike_crank_r",
    })
    post_cmd({
        "command_id": "c10_crank_r_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_15']"},
        "params": {"dx": 86.25, "dy": 65.0, "dz": 0.0},
        "idempotency_key": "k_bike_crank_r_move",
    })

    # Crank L
    c10_ck_l = post_cmd({
        "command_id": "c10_crank_l",
        "op": "box",
        "params": {"length": 172.5, "width": 14.0, "height": 32.0},
        "idempotency_key": "k_bike_crank_l",
    })
    post_cmd({
        "command_id": "c10_crank_l_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_16']"},
        "params": {"dx": -86.25, "dy": -65.0, "dz": 0.0},
        "idempotency_key": "k_bike_crank_l_move",
    })

    # Cassette at rear
    c10_cas = post_cmd({
        "command_id": "c10_cassette",
        "op": "cylinder",
        "params": {"radius": 68.0, "height": 38.0},
        "idempotency_key": "k_bike_cassette",
    })
    post_cmd({
        "command_id": "c10_cassette_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_17']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_cassette_rot",
    })
    post_cmd({
        "command_id": "c10_cassette_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_17']"},
        "params": {"dx": -418.0, "dy": 38.0, "dz": 70.0},
        "idempotency_key": "k_bike_cassette_move",
    })

    # 11. Cockpit: Stem & Drop Handlebar
    print("\n11. Cockpit Stem & Drop Handlebar...")
    c11_stem = post_cmd({
        "command_id": "c11_stem",
        "op": "box",
        "params": {"length": 110.0, "width": 38.0, "height": 38.0},
        "idempotency_key": "k_bike_stem",
    })
    post_cmd({
        "command_id": "c11_stem_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_18']"},
        "params": {"axis": "Y", "angle": -6.0},
        "idempotency_key": "k_bike_stem_rot",
    })
    post_cmd({
        "command_id": "c11_stem_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_18']"},
        "params": {"dx": 435.0, "dy": 0.0, "dz": 578.0},
        "idempotency_key": "k_bike_stem_move",
    })

    c11_bar = post_cmd({
        "command_id": "c11_bar_top",
        "op": "cylinder",
        "params": {"radius": 15.5, "height": 420.0},
        "idempotency_key": "k_bike_bar_top",
    })
    post_cmd({
        "command_id": "c11_bar_top_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_19']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_bar_top_rot",
    })
    post_cmd({
        "command_id": "c11_bar_top_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_19']"},
        "params": {"dx": 485.0, "dy": 0.0, "dz": 572.0},
        "idempotency_key": "k_bike_bar_top_move",
    })

    # 12. Seatpost & Ergonomic Short-Nose Saddle
    print("\n12. Seatpost & Saddle...")
    c12_sp = post_cmd({
        "command_id": "c12_seatpost",
        "op": "cylinder",
        "params": {"radius": 13.6, "height": 260.0},
        "idempotency_key": "k_bike_seatpost",
    })
    post_cmd({
        "command_id": "c12_sp_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_20']"},
        "params": {"axis": "Y", "angle": 16.5},
        "idempotency_key": "k_bike_sp_rot",
    })
    post_cmd({
        "command_id": "c12_sp_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_20']"},
        "params": {"dx": -175.0, "dy": 0.0, "dz": 585.0},
        "idempotency_key": "k_bike_sp_move",
    })

    c12_sad = post_cmd({
        "command_id": "c12_saddle",
        "op": "wedge",
        "params": {"length": 245.0, "width": 142.0, "height": 38.0, "top_length": 110.0},
        "idempotency_key": "k_bike_saddle",
    })
    post_cmd({
        "command_id": "c12_sad_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_21']"},
        "params": {"axis": "Y", "angle": -3.0},
        "idempotency_key": "k_bike_sad_rot",
    })
    post_cmd({
        "command_id": "c12_sad_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_21']"},
        "params": {"dx": -190.0, "dy": 0.0, "dz": 715.0},
        "idempotency_key": "k_bike_sad_move",
    })

    # 13. Disc Rotors (160mm)
    print("\n13. Front & Rear 160mm Disc Rotors...")
    c13_rf = post_cmd({
        "command_id": "c13_rotor_f",
        "op": "cylinder",
        "params": {"radius": 80.0, "height": 2.0},
        "idempotency_key": "k_bike_rotor_f",
    })
    post_cmd({
        "command_id": "c13_rf_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_22']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_rf_rot",
    })
    post_cmd({
        "command_id": "c13_rf_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_22']"},
        "params": {"dx": 587.0, "dy": -22.0, "dz": 70.0},
        "idempotency_key": "k_bike_rf_move",
    })

    c13_rr = post_cmd({
        "command_id": "c13_rotor_r",
        "op": "cylinder",
        "params": {"radius": 80.0, "height": 2.0},
        "idempotency_key": "k_bike_rotor_r",
    })
    post_cmd({
        "command_id": "c13_rr_rot",
        "op": "rotate",
        "target": {"base": "prev", "expr": "bodies['body_23']"},
        "params": {"axis": "X", "angle": 90.0},
        "idempotency_key": "k_bike_rr_rot",
    })
    post_cmd({
        "command_id": "c13_rr_move",
        "op": "translate",
        "target": {"base": "prev", "expr": "bodies['body_23']"},
        "params": {"dx": -418.0, "dy": -22.0, "dz": 70.0},
        "idempotency_key": "k_bike_rr_move",
    })

    print("\n=== Merida SCULTURA ENDURANCE 6000 Assembly Built Successfully! ===")


if __name__ == "__main__":
    main()
