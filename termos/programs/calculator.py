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


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return float(_OPS[type(node.op)](_eval_node(node.operand)))
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and right == 0:
            raise ProgramError("calc: division by zero")
        return float(_OPS[type(node.op)](left, right))
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    raise ProgramError("calc: invalid expression")


class CalculatorProgram(Program):
    name = "calc"
    description = "Evaluate a basic arithmetic expression"
    memory_mb = 4.0

    def run(self, kernel: Kernel, shell: Shell, args: list[str]) -> int:
        if not args:
            raise ProgramError("calc: missing expression")
        result = safe_eval(" ".join(args))
        if result.is_integer():
            print(int(result))
        else:
            print(result)
        return 0
