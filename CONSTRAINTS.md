# Constraints

Last reviewed: 2026-10-24

## Floor (Always Enforced)

- No suppression comments: `# type: ignore`, `# noqa`, `@ts-ignore`, `eslint-disable`.
- No unimplemented stubs: `raise NotImplementedError`, empty `except: pass`, empty `catch {}`.
- No skipped or deleted tests without explicit reason in the commit.
- No secrets or credentials in source.
- This file does not get weakened to make a change pass.

## Comment Constraints (Strict Design & First-Principles Rules)

All code comments in this project (both Python backend and JavaScript frontend) must strictly adhere to the following four golden rules:

1. **No Document References (零文档引用)**
   - Comments must never reference internal or external documents, specifications, architecture decision records, pull requests, issues, RFCs, or hyperlinks (e.g., no occurrences of `ADR-xxx`, `SPEC-xxx`, `PR #xx`, `Issue #xx`, external web links, or documentation file paths).
   - Code must remain self-contained and self-explanatory.

2. **No Procedural Steps or Plan Tracking (零过程性步骤与计划记录)**
   - Comments must never record development phases, task plans, execution milestones, or procedural step numbering (e.g., no `Step 1 / Step 2`, `Phase 1 / Phase 2`, `// --- 1. xxx ---`, `TODO`, `FIXME`).
   - Comments represent the completed, invariant design of the system, not the historical trail of how the code was written.

3. **First-Principles Design Intent (回归第一性作用：解释代码设计)**
   - Comments exist solely to explain code design, architectural intent, algorithm rationale, data structure invariants, and non-obvious engineering decisions.
   - Comments answer "why it is designed this way" rather than repeating what the code syntax trivially reveals.

4. **Unified Formatting (统一格式风格)**
   - **Python**: Standard concise Docstrings for modules, classes, and public functions describing responsibility; inline comments use `# <Design explanation>` without decorative dividers.
   - **JavaScript**: JSDoc blocks for exported modules, classes, and primary state handlers; inline comments use `// <Design explanation>` without decorative ASCII banners (e.g., no `// --- Section ---`).
   - Tone must remain objective, concise, and focused on domain mechanics.

## Enforced with Numbers

| Dimension | Rule | Checked by | Runs at |
|-----------|------|------------|---------|
| Tests | All unit & E2E tests pass with zero failures | `python -m unittest discover -s tests` | every task end |
| Backend Module Size | Single Python module ≤ 400 lines | Line count verification | every task end |
| Frontend Module Size | Single JavaScript module ≤ 350 lines | Line count verification | every task end |
| Memory Lifecycle | All WebGL geometry updates must call `.dispose()` | Static audit & browser runtime | review |
| Sandbox Security | AST whitelist audit restricts execution to safe modules | `workspace.validate_code_ast` | execution time |

## Exceptions

None currently active.
