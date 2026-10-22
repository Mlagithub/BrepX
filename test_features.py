import smlibpy
from smlibpy import Box, Cylinder, Sphere, Cone, Torus, Z, X, Y

print("smlibpy version:", getattr(smlibpy, '__version__', 'unknown'))

# 1. Flange plate example
plate = Box(100, 80, 12)
try:
    # Test fillet on vertical edges
    plate = plate.fillet(plate.edges().parallel_to(Z), 10)
    print("Fillet succeeded, volume:", plate.volume)
except Exception as e:
    print("Fillet exception:", e)

# 2. Add center hole and mounting holes
try:
    center_hole = Cylinder(15, 20)
    plate = plate - center_hole
    print("Center hole cut succeeded, volume:", plate.volume)
except Exception as e:
    print("Hole exception:", e)

# 3. Export to gltf
plate.export("test_outputs/flange.gltf")
print("Flange exported to gltf, size:", len(open("test_outputs/flange.gltf", "rb").read()))
