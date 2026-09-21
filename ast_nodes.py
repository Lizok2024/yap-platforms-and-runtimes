from abc import ABC, abstractmethod
from typing import Any

from context import ExecutionContext


def truth(value: Any) -> bool:
    return value != 0


class ASTNode(ABC):

    @abstractmethod
    def eval(self, ctx: ExecutionContext) -> Any:
        pass


class SkipNode(ASTNode):
    def eval(self, ctx: ExecutionContext) -> Any:
        return None


class ConstNode(ASTNode):
    def __init__(self, value: Any) -> None:
        self.value = int(value)

    def eval(self, ctx: ExecutionContext) -> Any:
        return self.value


class VarNode(ASTNode):
    def __init__(self, name: Any) -> None:
        self.name = str(name)

    def eval(self, ctx: ExecutionContext) -> Any:
        return ctx.env.get(self.name)


class SeqNode(ASTNode):
    def __init__(self, statements: list[ASTNode | None]) -> None:
        self.statements = [s for s in statements if s is not None]

    def eval(self, ctx: ExecutionContext) -> Any:
        result = None
        for stmt in self.statements:
            result = stmt.eval(ctx)
        return result


class AssignNode(ASTNode):
    def __init__(self, target: Any, expr: ASTNode) -> None:
        self.target = str(target)
        self.expr = expr

    def eval(self, ctx: ExecutionContext) -> Any:
        val = self.expr.eval(ctx)
        ctx.env.set(self.target, val)
        return val


class CompoundAssignNode(ASTNode):
    def __init__(self, target: Any, op: str, expr: ASTNode) -> None:
        self.target = str(target)
        self.op = op
        self.expr = expr

    def eval(self, ctx: ExecutionContext) -> Any:
        old_val = ctx.env.get(self.target)
        val = self.expr.eval(ctx)
        new_val = BinOpNode._apply_op(self.op, old_val, val)
        ctx.env.set(self.target, new_val)
        return new_val


class ReadNode(ASTNode):
    def __init__(self, target: Any) -> None:
        self.target = str(target)

    def eval(self, ctx: ExecutionContext) -> Any:
        val = ctx.read_int()
        ctx.env.set(self.target, val)
        return val


class WriteNode(ASTNode):
    def __init__(self, expr: ASTNode) -> None:
        self.expr = expr

    def eval(self, ctx: ExecutionContext) -> Any:
        val = self.expr.eval(ctx)
        ctx.write(val)
        return val


class WhileNode(ASTNode):
    def __init__(self, cond: ASTNode, body: ASTNode | None) -> None:
        self.cond = cond
        self.body = body

    def eval(self, ctx: ExecutionContext) -> Any:
        while truth(self.cond.eval(ctx)):
            if self.body:
                self.body.eval(ctx)
        return None


class DoWhileNode(ASTNode):
    def __init__(self, body: ASTNode | None, cond: ASTNode) -> None:
        self.body = body
        self.cond = cond

    def eval(self, ctx: ExecutionContext) -> Any:
        while True:
            if self.body:
                self.body.eval(ctx)
            if not truth(self.cond.eval(ctx)):
                break
        return None


class ForNode(ASTNode):
    def __init__(
        self,
        init: ASTNode | None,
        cond: ASTNode | None,
        update: ASTNode | None,
        body: ASTNode | None,
    ) -> None:
        self.init = init
        self.cond = cond
        self.update = update
        self.body = body

    def eval(self, ctx: ExecutionContext) -> Any:
        if self.init:
            self.init.eval(ctx)
        while True:
            if self.cond and not truth(self.cond.eval(ctx)):
                break
            if self.body:
                self.body.eval(ctx)
            if self.update:
                self.update.eval(ctx)
        return None


class IfNode(ASTNode):
    def __init__(
        self,
        cond: ASTNode,
        then_branch: ASTNode | None,
        else_branch: ASTNode | None = None,
    ) -> None:
        self.cond = cond
        self.then_branch = then_branch
        self.else_branch = else_branch

    def eval(self, ctx: ExecutionContext) -> Any:
        if truth(self.cond.eval(ctx)):
            return self.then_branch.eval(ctx) if self.then_branch else None
        elif self.else_branch:
            return self.else_branch.eval(ctx)
        return None


class BinOpNode(ASTNode):
    def __init__(
        self, op: str, left: ASTNode | None, right: ASTNode | None = None
    ) -> None:
        self.op = op
        self.left = left
        self.right = right

    def eval(self, ctx: ExecutionContext) -> Any:
        left_val = self.left.eval(ctx) if self.left else None

        if self.op == "!" and self.right is None:
            return UnOpNode._apply_op(self.op, left_val)

        right_val = self.right.eval(ctx) if self.right else None
        return self._apply_op(self.op, left_val, right_val)

    @staticmethod
    def _apply_op(op: str, left: Any, right: Any) -> Any:
        if op in ("+", "Plus"):
            return left + right
        if op in ("-", "Minus"):
            return left - right
        if op in ("*", "Star"):
            return left * right
        if op in ("/", "Slash"):
            return left // right
        if op in ("%", "Percent"):
            return left % right
        if op in ("==", "Eq", "Equal"):
            return 1 if left == right else 0
        if op in ("!=", "Ne", "NotEqual"):
            return 1 if left != right else 0
        if op in ("<", "Lt"):
            return 1 if left < right else 0
        if op in ("<=", "Le"):
            return 1 if left <= right else 0
        if op in (">", "Gt"):
            return 1 if left > right else 0
        if op in (">=", "Ge"):
            return 1 if left >= right else 0
        if op in ("&&", "and", "And", "LogicalAnd"):
            return 1 if (truth(left) and truth(right)) else 0
        if op in ("||", "or", "Or", "LogicalOr"):
            return 1 if (truth(left) or truth(right)) else 0
        raise ValueError(f"Unknown binary operator: {op}")


class UnOpNode(ASTNode):
    def __init__(self, op: str, operand: ASTNode) -> None:
        self.op = op
        self.operand = operand

    def eval(self, ctx: ExecutionContext) -> Any:
        val = self.operand.eval(ctx)
        return self._apply_op(self.op, val)

    @staticmethod
    def _apply_op(op: str, value: Any) -> Any:
        if op in ("!", "not", "Not", "LogicalNot"):
            return 1 if not truth(value) else 0
        if op in ("-", "Minus"):
            return -value
        if op in ("+", "Plus"):
            return value
        raise ValueError(f"Unknown unary operator: {op}")
