from smlibpy import Box, Cylinder, Z, show
import os

print("Testing smlibpy...")
part = Box(80, 60, 10)
print(f"Initial Box Volume: {part.volume}")

# Add holes
hole = Cylinder(8, 20)
part = part - hole
print(f"Box with Hole Volume: {part.volume}")

# Export formats
os.makedirs("test_outputs", exist_ok=True)
part.export("test_outputs/part.step")
part.export("test_outputs/part.stl")
try:
    part.export("test_outputs/part.gltf")
except Exception as e:
    print(f"glTF export note: {e}")

print("Exports completed successfully:")
for f in os.listdir("test_outputs"):
    print(" -", f, os.path.getsize(os.path.join("test_outputs", f)), "bytes")
