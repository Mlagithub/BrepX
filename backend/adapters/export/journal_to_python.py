"""One-way unidirectional projection from Command Journal to standalone Python script."""

from __future__ import annotations

from backend.core.design import Design


def journal_to_python(design: Design) -> str:
    lines: list[str] = [
        "# Auto-generated standalone Python reproduction script from BrepX Command Journal",
        "# Note: This is a strictly one-way projection and cannot be re-imported as model definition.",
        "",
        "from __future__ import annotations",
        "import smlibpy",
        "from backend.session import Session",
        "from backend.core.command import Command",
        "",
        "def build_model():",
        "    session = Session()",
    ]

    if not design.journal:
        lines.append("    # Empty design journal")
        lines.append("    return session.design.geometry")
        return "\n".join(lines)

    for idx, record in enumerate(design.journal, start=1):
        cmd = record.command
        target_repr = f"{{'base': '{cmd.target.base}', 'expr': '{cmd.target.expr}'}}" if cmd.target else "None"
        tool_repr = f"{{'base': '{cmd.tool.base}', 'expr': '{cmd.tool.expr}'}}" if cmd.tool else "None"

        lines.append(f"    # Command {idx}: {cmd.op} (id: {cmd.command_id})")
        lines.append("    session.submit(Command.from_payload({")
        lines.append(f"        'command_id': {cmd.command_id!r},")
        lines.append(f"        'op': {cmd.op!r},")
        lines.append(f"        'target': {target_repr},")
        lines.append(f"        'tool': {tool_repr},")
        lines.append(f"        'params': {cmd.params!r},")
        lines.append(f"        'idempotency_key': {cmd.idempotency_key!r},")
        lines.append("    }))")

    lines.append("")
    lines.append("    return session.design.geometry")
    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    part = build_model()")
    lines.append("    print('Constructed geometry volume:', getattr(part, 'volume', 0.0))")
    lines.append("")

    return "\n".join(lines)
