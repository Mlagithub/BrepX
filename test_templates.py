from server import build_parametric_part, export_part_to_gltf

for t in ["flange", "bracket", "bushing", "csg_demo"]:
    print(f"Testing template: {t}")
    part, script = build_parametric_part(t, {})
    print(f"  Volume: {part.volume:.2f}")
    gltf = export_part_to_gltf(part, t)
    print(f"  glTF size: {len(gltf)} chars")
    print(f"  Script preview:\n{script[:120]}...\n")

print("All templates built successfully!")
