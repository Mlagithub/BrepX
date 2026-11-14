---
name: brepx-plan
description: Work the CAD plan, from opening a document and reading state through node edits, compile, run one ready node, and failure recovery.
---

# The plan workflow

The plan is the source of truth above the document. It records the goal, the
feature nodes, their dependencies and their acceptance checks. The compiler
validates the plan and lowers it to kernel actions; you never write kernel calls.

## Tools

| Tool | Use |
|---|---|
| `new_document` | create a blank document for a new modeling request |
| `documents` | list existing documents; choose one to continue |
| `state` | version, features, checks, plan summary, pending notes |
| `plan` | full node list with status, params, refs, expectations and observations |
| `plan_schema` | exact node / ref / filter / op shapes; call this first if unsure |
| `plan_add_node` | add exactly one node; use this for every node of a large plan |
| `plan_edit` | `ops` = add_node / update_node / remove_node / set_goal |
| `blend_group` | fillet/chamfer a whole edge set; retries per edge when the group fails |
| `thread` | cut a helical external thread groove into a target, or make the thread tool |
| `stepped_bore` | cut one or two coaxial bores along X/Y/Z, with a through second stage |
| `plan_compile` | dry-run the tree: issues, op count, action coverage |
| `plan_run` | execute one ready node; a feature commits a milestone, a check measures |
| `probe` | dry-run a selector or resolve a picked face |
| `render` | qualitative multi-view check of the current part |
| `catalog` | generated actions, their roles and parameter schemas |

## Start a request

A message that starts with `[当前文档 <id> ...]` already names the document the
user is working in. That document is open for this turn: call `state` with its
id and edit it. Do not create a new document and do not ask which document.
Otherwise, for a new request, call `new_document` and keep its document id for
every following call. For a follow-up without that tag, use `documents` to find
the document and pass its id. Never mutate a document other than the one named
in this turn or one you created in this conversation.

## Node shape

```json
{
  "id": "plate",
  "kind": "feature",
  "title": "80x80x20 plate",
  "action": "k_box",
  "params": {"length": 80, "width": 80, "height": 20},
  "refs": {},
  "deps": [],
  "expect": []
}
```

A cut node references earlier features:

```json
{
  "id": "hole",
  "kind": "feature",
  "title": "cut the bore",
  "action": "k_cut",
  "params": {},
  "refs": {
    "target": {"source": "plate", "select": "self"},
    "others": [{"source": "tool", "select": "self"}]
  },
  "deps": ["plate", "tool"],
  "expect": []
}
```

- `kind`: `goal`, `feature` or `check`. `check` needs `deps` and `expect`.
- `refs`: `source` is an earlier feature id; `select` is `self`, `faces`,
  `edges`, `vertices` or `wires`; optional `filters` are selector calls such as
  `{"method": "nearest", "args": [[0, 0, 10]]}`.
- `deps` must name earlier nodes; they gate `plan_run`.
- `expect`: `volume`, `area`, `faces`, `edges`, `solids`, `watertight`,
  `bbox_size`, `bbox_min`, `bbox_max`, `distance`, `intersects`; ops
  `ge`, `le`, `between`, `eq`, `true`.

## Ops

```json
{"op": "add_node", "node": {"id": "plate", "kind": "feature", "...": "..."}}
{"op": "update_node", "node": {"id": "plate", "params": {"length": 100}}}
{"op": "remove_node", "id": "plate"}
{"op": "set_goal", "goal": "plate with a bore"}
```

`update_node` replaces the whole `params` object, so include every required
parameter. If a node is failed or stale, update it and run it again.

## Loop

1. `new_document` or `documents` + `state`.
2. If no plan, `plan_edit` with `set_goal` and the first feature nodes.
   For a plan with more than two nodes, add them one at a time with
   `plan_add_node`; never put the whole plan in one tool argument.
3. `plan_compile`; fix every issue before running geometry.
4. `plan_run` a ready node. On success the plan reports `done`, the document
   version and the measured metrics. On failure the node is `failed`, the
   document is unchanged (except a successful commit), and later nodes stay
   blocked.
5. For an incremental change, update only the affected node and run it, then
   run its dependent checks. Do not rebuild untouched nodes.
6. Render and inspect the result after a visual change; export STEP/STL only
   when the user asks.

## When to stop and ask

Ask one question when the intent is missing a decision that changes geometry:
flow rate/speed, material, tolerance, blade count, or which face the feature
must sit on. Record the answer in the node's note; do not guess silently.

## Failure codes

| Code | Meaning | Action |
|---|---|---|
| `PLAN_INVALID` | structural problem | fix ids, kind, deps, refs, expect |
| `NODE_NOT_READY` | a dependency is not done | run the dependency first |
| `ACTION_UNKNOWN` | action not in the catalogue | inspect `catalog` |
| `EXPECT_FAILED` | built but failed its check | change geometry, not the check |
| `REF_RETARGETED` | the face/edge moved after an upstream edit | re-pick and update the ref |
| `PLAN_STALE` | plan based on an older version | re-read and update nodes |
| `BUILD_FAILED` | kernel rejected the geometry | read the hint, fix parameters |

## Rules

- One node = one generated action; do not hide a multi-step macro in a node.
- Checks are part of the plan, not optional commentary.
- Human review sits at the intent and milestone level; do not ask for approval
  of every node.
