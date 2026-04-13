"""Utility tool handlers (e.g., calculator)."""
from __future__ import annotations

import ast
import logging
import operator
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_ALLOWED_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARYOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_EXPRESSION_PATTERN = re.compile(r"[\d\.]+|[\+\-\*\/\%\^\(\)]")


def handle_calculator(query: str) -> Dict[str, object]:
    """Attempt to evaluate a math expression from the query."""
    expression = _extract_expression(query)
    if not expression:
        return {"handled": False, "result": None}

    try:
        value = _safe_eval(expression)
        return {
            "handled": True,
            "result": f"The result of {expression} is {value}.",
        }
    except Exception as exc:
        logger.error("Calculator tool failed: %s", exc)
        return {"handled": False, "result": None}


def _extract_expression(query: str) -> Optional[str]:
    tokens = _EXPRESSION_PATTERN.findall(query or "")
    expression = "".join(tokens)
    return expression or None


def _safe_eval(expression: str) -> float:
    node = ast.parse(expression, mode="eval")
    return _eval_node(node.body)


def _eval_node(node):
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        return _ALLOWED_BINOPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
        operand = _eval_node(node.operand)
        return _ALLOWED_UNARYOPS[type(node.op)](operand)
    raise ValueError("Unsupported expression")
