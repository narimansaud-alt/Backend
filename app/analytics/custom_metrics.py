import ast
from dataclasses import dataclass
from decimal import Decimal, DivisionByZero, InvalidOperation
from typing import Any, cast


class InvalidMetricExpression(ValueError):
    pass


ALLOWED_BINARY = (ast.Add, ast.Sub, ast.Mult, ast.Div)
ALLOWED_UNARY = (ast.UAdd, ast.USub)


@dataclass(frozen=True)
class MetricExpression:
    tree: ast.Expression

    @classmethod
    def parse(
        cls,
        expression: str,
        allowed_metrics: set[str],
        *,
        max_nodes: int = 64,
        max_depth: int = 12,
    ) -> MetricExpression:
        if len(expression) > 512:
            raise InvalidMetricExpression("Metric expression is too long")
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            raise InvalidMetricExpression("Metric expression has invalid syntax") from exc
        nodes = list(ast.walk(tree))
        if len(nodes) > max_nodes:
            raise InvalidMetricExpression("Metric expression is too complex")

        def validate(node: ast.AST, depth: int = 0) -> None:
            if depth > max_depth:
                raise InvalidMetricExpression("Metric expression is too deeply nested")
            if isinstance(node, ast.Expression):
                validate(node.body, depth + 1)
            elif isinstance(node, ast.BinOp) and isinstance(node.op, ALLOWED_BINARY):
                validate(node.left, depth + 1)
                validate(node.right, depth + 1)
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ALLOWED_UNARY):
                validate(node.operand, depth + 1)
            elif isinstance(node, ast.Name):
                if node.id not in allowed_metrics:
                    raise InvalidMetricExpression(f"Unknown metric: {node.id}")
            elif isinstance(node, ast.Constant):
                if isinstance(node.value, bool) or not isinstance(node.value, int | float):
                    raise InvalidMetricExpression("Only numeric literals are allowed")
            else:
                raise InvalidMetricExpression(f"Unsupported expression element: {type(node).__name__}")

        validate(tree)
        return cls(tree=tree)

    def to_dict(self) -> dict[str, Any]:
        def convert(value: Any) -> Any:
            if isinstance(value, ast.AST):
                return {
                    "type": type(value).__name__,
                    **{name: convert(field) for name, field in ast.iter_fields(value)},
                }
            if isinstance(value, list):
                return [convert(item) for item in value]
            return value

        return cast(dict[str, Any], convert(self.tree))

    def evaluate(self, metrics: dict[str, Decimal | None]) -> Decimal | None:
        def visit(node: ast.AST) -> Decimal | None:
            if isinstance(node, ast.Expression):
                return visit(node.body)
            if isinstance(node, ast.Name):
                return metrics.get(node.id)
            if isinstance(node, ast.Constant):
                return Decimal(str(node.value))
            if isinstance(node, ast.UnaryOp):
                value = visit(node.operand)
                if value is None:
                    return None
                return value if isinstance(node.op, ast.UAdd) else -value
            if isinstance(node, ast.BinOp):
                left, right = visit(node.left), visit(node.right)
                if left is None or right is None:
                    return None
                try:
                    if isinstance(node.op, ast.Add):
                        return left + right
                    if isinstance(node.op, ast.Sub):
                        return left - right
                    if isinstance(node.op, ast.Mult):
                        return left * right
                    if isinstance(node.op, ast.Div):
                        return None if right == ZERO else left / right
                except DivisionByZero, InvalidOperation:
                    return None
            raise InvalidMetricExpression("Expression was not validated")

        return visit(self.tree)


ZERO = Decimal("0")
