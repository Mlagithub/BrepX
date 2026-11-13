---
name: impeller
description: Build and edit the impeller through the CAD plan. Use when asked to model, change or check a centrifugal impeller, its hub, blades, boundaries or fluid domain.
---

# Impeller plan

Work with the plan, not with ad-hoc feature calls. Read `state` first (version,
plan summary, pending intents), then `plan` for the full tree. Every node is a
generated kernel action; the compiler writes the kernel code.

## Node order (defaults)

| id | action | params | refs |
|---|---|---|---|
| hub_profile | `k_polygon` | points `[[0,0],[45,0],[45,-4],[0,-4]]` | - |
| hub_profile_placed | `place_on` | plane `XZ` | shape hub_profile |
| hub | `k_revolve` | angle 360, axis `Z` | profile hub_profile_placed |
| blade_{i}_section | `k_rectangle` | width 3, height 20 | - |
| blade_{i}_placed | `place_on` | plane `YZ` | shape blade_{i}_section |
| blade_{i}_leaned | `k_rotate` | axis `X`, angle 25 + 10u | target blade_{i}_placed |
| blade_{i}_stationed | `k_translate` | x 18 + 26u, z 8 | target blade_{i}_leaned |
| blade_{i}_wrapped | `k_rotate` | axis `Z`, angle wrap*u | target blade_{i}_stationed |
| b_loft | `k_loft` | - | sections blade_{i}_wrapped |
| b_pattern | `pattern` | kind circular, count 9, radius 0 | target b_loft |
| b_fuse | `k_fuse` | - | target hub, others (b_pattern) |
| b_fillet | `k_fillet` | radius 0.3 | target b_fuse, edges nearest([44,0,20]) |
| t_in / t_out / t_wall | `tag_boundary` | inlet / outlet / wall | faces nearest([0,0,0]) / largest() / planar() |
| fluid_cavity | `cavity` | r_env 2, z_pad 2 | target b_fillet |

`u = i / (sections - 1)`. The blade root sits at z = 8, so the 20 mm blade
overlaps the 4 mm back disc and the fused body is one solid. Start with 5
sections and 9 blades; increase only after the plan compiles and the first
blade builds.

## Workflow

1. `state` to confirm the document version and whether a plan exists.
2. `plan_edit` with `ops=[{"op":"add_node","node":{...}}]` to add nodes; use
   `goal` once. `plan_compile` checks refs/actions/params without geometry.
3. `plan_run` one ready node at a time. A feature node commits its milestone;
   a check node only measures. Stop at the first failure and fix the node.
4. `probe` for a dry-run selector or a picked point; `render` for a visual
   check; `state` for checks/metrics.
5. Re-run `plan_run` after a parameter change; nodes whose feature still exists
   are skipped, changed nodes are re-run.

## Parameter ranges

- hub: `r_out` 30-60 mm, back thickness 3-8 mm, `z_out` 0.
- blade: `r_in` 15-25, `r_out` <= hub `r_out`, `b_out` 15-35, lean 15-40 deg,
  wrap 20-60 deg, thickness >= 1.5 mm, sections 5-8.
- fillet: <= half the blade thickness; 0.3 mm on a 3 mm blade.
- cavity: `r_env` 1-5 mm, `z_pad` 1-5 mm.

## Failures and fixes

| Code / hint | Cause | Fix |
|---|---|---|
| `sections should be closed, ordered and not intersect` | loft sections are duplicated or cross | translate each section before lofting; keep the order by Z |
| `draft: ... parallel to the neutral plane` | drafting a top/bottom face | draft a side wall, or change `neutral_plane` |
| `CHECK_FAILED valid` after fillet | radius too large for the blade | reduce to <= 2.6 mm on a 3 mm blade |
| `REF_EMPTY` | selector matched nothing | fix the parent or widen `nearest` |
| `REF_AMBIGUOUS` | selector matched many | add `largest()` / `one()` / `nearest` |
| `REF_RETARGETED` | the face moved after an upstream edit | re-pick the face and update the ref |
| `PLAN_STALE` | the plan is based on an older version | re-read `plan`, update the changed nodes |
| watertight false on cavity | envelope smaller than the body | increase `r_env`/`z_pad` |

## Rules

- Face refs are semantic (`nearest`, `largest`, `planar`, `one`), never indices.
- Select a face through `planar` first when a nearby curved face could win the
  nearest test: `Ref("b_fillet", "faces", (Filter("planar"), Filter("nearest", [44,0,-4])))`.
- A boolean needs overlap, not tangency; sink the tool 0.5-1 mm into the body.
- The face centroid moves when upstream geometry changes; for a fixed position
  use a plane (`place_on` plane + offset) instead of a face.
- Do not write kernel calls or a `run_script`; the compiler owns that.
