# Agent Guidelines for BrepX

Read `CONSTRAINTS.md` before writing code. Do not weaken it to make a change pass.

## Core Rules for All Agents

1. **Comment Integrity**:
   - Never reference documents, ADRs, specs, issues, or URLs in code comments.
   - Never include procedural step records, phase numbers, execution plans, or task step markers (e.g., `Step 1`, `Phase 1`, `1. ...`).
   - Comments must serve their first-principles purpose: explain the rationale, design intent, data structures, and invariants of the code.
   - Maintain uniform comment formatting across Python and JavaScript files.

2. **Quality Bar**:
   - Keep backend files under 400 lines and frontend files under 350 lines.
   - Run `python -m unittest discover -s tests` to ensure zero regressions before reporting completion.
   - Do not add `@ts-ignore`, `# noqa`, `# type: ignore`, or empty error-suppression blocks.
