---
name: volute
description: Build a spiral volute casing from a generated plan. Use when asked to model a volute, a growing spiral channel, or a swept casing.
---

# Volute plan

A volute is a spiral centre line, a growing section and a swept casing. It is
not a document type; it is four generated nodes.

| id | action | params | refs |
|---|---|---|---|
| v1 | `k_spiral` | start_radius 30, end_radius 70, turns 1.25, plane `XY` | — |
| v2 | `k_rectangle` | width 8, height 20 | — |
| v3 | `k_sweep` | scale_start 0.35, scale_end 1.0, orient true | profile v2, path v1 |
| v4 | `k_shell` | thickness 1.0, outward false, corners `round` | target v3 |

`plan_compile` first; then `plan_run` v1…v4. The shell fails when the wall is
thicker than the smallest section radius or when the sweep self-intersects:
reduce `width`, increase the start radius, or turn the shell off and keep the
solid channel.

A volute that must sit on a picked face: add a `place_on` node after v1 with the
face ref, or sweep in a plane built from that face. For a face that is not
planar, use the face's `wrap` curve (generated `k_face_wrap`) as the sweep path;
expect stretching away from the face's parameter lines.

Checks: `solids == 1`, `watertight`, volume > 0. Add a `tag_boundary` for the
outlet if the casing is used for flow.
