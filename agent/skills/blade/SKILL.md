---
name: blade
description: Build a twisted hollow blade from a generated plan. Use for a single blade, a duct vane or a twisted loft that must be shelled.
---

# Blade plan

One twisted loft, then a shell. The section is a rectangle placed on `YZ`,
leaned about X, moved to its radius and wrapped about Z.

| id | action | params | refs |
|---|---|---|---|
| s{i}a | `k_rectangle` | width 3, height b_out | — |
| s{i}b | `place_on` | plane `YZ` | shape s{i}a |
| s{i}c | `k_rotate` | axis `X`, angle 25 + 10u | target s{i}b |
| s{i}d | `k_translate` | x 18 + 26u, z b_out/2 | target s{i}c |
| s{i}e | `k_rotate` | axis `Z`, angle wrap*u | target s{i}d |
| b_loft | `k_loft` | — | sections s0e…s5e |
| b_shell | `k_shell` | thickness 1.0, outward false | target b_loft |

`u = i / (sections - 1)`. Keep the sections ordered and non-intersecting; a
loft of two coincident rectangles fails with "sections should be closed,
ordered and not intersect each other". Watch the shell: a thickness near the
blade thickness closes the two walls; keep it ≤ 0.4 × t.

If the blade must be attached to a hub, add `k_fuse` with the hub body; ensure
the root overlaps the hub by 0.5–1 mm, not just touches it.
