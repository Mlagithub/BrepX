"""Wing compiler namespace.

The wing compiler is introduced with the wing OML stage. Keeping the namespace
separate leaves room for fuselage and tail compilers without changing the
aircraft package surface.
"""

from __future__ import annotations

NODE_KINDS: tuple[object, ...] = ()
