"""Safe calculator program."""

from __future__ import annotations

import ast
import operator
from typing import TYPE_CHECKING

from core.errors import ProgramError
from programs.program import Program

if TYPE_CHECKING:
    from kernel.kernel import Kernel
    from shell.shell import Shell

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def safe_eval(expression: str) -> float:
    """Evaluate a basic arithmetic expression without Python eval()."""
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ProgramError("calc: invalid expression") from exc
    return float(_eval_node(tree.body))

