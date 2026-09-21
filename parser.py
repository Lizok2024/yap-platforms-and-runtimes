from typing import Any, Optional

from ast_nodes import (
    AssignNode,
    ASTNode,
    BinOpNode,
    CompoundAssignNode,
    ConstNode,
    DoWhileNode,
    ForNode,
    IfNode,
    ReadNode,
    SeqNode,
    SkipNode,
    UnOpNode,
    VarNode,
    WhileNode,
    WriteNode,
)


class ASTParser:

    @staticmethod
    def _get(data: Any, *keys: str, default: Any = None) -> Any:
        if not isinstance(data, dict):
            return default
        for k in keys:
            if k in data:
                return data[k]
        return default

    @classmethod
    def _extract_name(cls, val: Any) -> Any:
        if isinstance(val, dict):
            return cls._get(val, "name", "var", "id", "value", "target", "dst", default=val)
        return val

    @classmethod
    def parse(cls, raw: Any) -> Optional[ASTNode]:
        if raw is None:
            return None

        if isinstance(raw, (int, float)):
            return ConstNode(raw)
        if isinstance(raw, str):
            return VarNode(raw)
        if isinstance(raw, list):
            nodes = [cls.parse(item) for item in raw]
            return SeqNode([n for n in nodes if n is not None])

        if not isinstance(raw, dict):
            return ConstNode(raw)

        data = dict(raw)
        data.pop("input", None)

        if not data:
            return SkipNode()

        node_type: Optional[str] = None
        payload: Any = data

        for type_key in ("type", "kind", "nodeType", "tag"):
            if type_key in data:
                node_type = str(data[type_key])
                break

        if node_type is None:
            if len(data) == 1:
                k = next(iter(data))
                node_type = k
                payload = data[k]
            else:
                for tag in (
                    "seq", "while", "dowhile", "for", "if", "binop", "binary",
                    "assn", "assign", "compoundassign", "read", "write", "unary"
                ):
                    if tag in data:
                        node_type = tag
                        payload = data[tag] if isinstance(data[tag], dict) else data
                        break

        if node_type is None:
            if "value" in data:
                return ConstNode(data["value"])
            if "name" in data or "var" in data:
                return VarNode(cls._extract_name(data))
            return SkipNode()

        node_type = str(node_type).lower().replace("_", "")

        if node_type in ("program", "block"):
            body = cls._get(payload, "body", "statements", "children", "stmts", default=[])
            return cls.parse(body)

        elif node_type in ("seq", "sequence"):
            if isinstance(payload, list):
                nodes = [cls.parse(item) for item in payload]
                return SeqNode([n for n in nodes if n is not None])
            if isinstance(payload, dict):
                if "left" in payload or "right" in payload or "first" in payload or "second" in payload:
                    left = cls.parse(cls._get(payload, "left", "first", "lhs"))
                    right = cls.parse(cls._get(payload, "right", "second", "rhs"))
                    return SeqNode([left, right])
            return cls.parse(payload)

        elif node_type in ("stmt", "statement"):
            inner = cls._get(payload, "stmt", "statement", "value")
            return cls.parse(inner if inner is not None else payload)

        elif node_type == "read":
            target = payload if isinstance(payload, str) else cls._get(payload, "name", "var", "id", "target", "value", "dst")
            target = cls._extract_name(target)
            return ReadNode(target)

        elif node_type == "write":
            expr = payload
            if isinstance(payload, dict) and any(k in payload for k in ("expr", "expression", "value", "arg", "var")):
                expr = cls._get(payload, "expr", "expression", "value", "arg", default=payload)
            return WriteNode(cls.parse(expr))

        elif node_type in ("assign", "assn"):
            target = cls._get(payload, "target", "dst", "name", "left", "id", "var")
            target = cls._extract_name(target)
            expr = cls._get(payload, "expr", "src", "expression", "value", "right")
            return AssignNode(target, cls.parse(expr))

        elif node_type in ("compoundassign", "compoundassn"):
            target = cls._get(payload, "target", "dst", "name", "left", "id", "var")
            target = cls._extract_name(target)
            op = cls._get(payload, "op", "operator")
            expr = cls._get(payload, "expr", "src", "expression", "value", "right")
            return CompoundAssignNode(target, op, cls.parse(expr))

        elif node_type == "while":
            cond = cls._get(payload, "cond", "condition", "test")
            body = cls._get(payload, "body", "stmt", "do", "block")
            return WhileNode(cls.parse(cond), cls.parse(body))

        elif node_type == "dowhile":
            body = cls._get(payload, "body", "stmt", "do", "block")
            cond = cls._get(payload, "cond", "condition", "test")
            return DoWhileNode(cls.parse(body), cls.parse(cond))

        elif node_type == "for":
            init = cls._get(payload, "init", "initializer", "start")
            cond = cls._get(payload, "cond", "condition", "test")
            update = cls._get(payload, "update", "increment", "step")
            body = cls._get(payload, "body", "stmt", "do", "block")
            return ForNode(cls.parse(init), cls.parse(cond), cls.parse(update), cls.parse(body))

        elif node_type in ("if", "elif"):
            cond = cls._get(payload, "cond", "condition", "test")
            then_b = cls._get(payload, "then", "consequent", "ifTrue", "body")
            else_b = cls._get(payload, "else", "alternate", "ifFalse", "elsePart")
            return IfNode(cls.parse(cond), cls.parse(then_b), cls.parse(else_b))

        elif node_type in ("binary", "binaryop", "binop"):
            op = cls._get(payload, "op", "operator", "binop")
            left = cls.parse(cls._get(payload, "left", "lhs", "first"))
            right = cls.parse(cls._get(payload, "right", "rhs", "second"))
            return BinOpNode(op, left, right)

        elif node_type in ("unary", "unop"):
            op = cls._get(payload, "op", "operator")
            operand = cls.parse(cls._get(payload, "operand", "expr", "value", "arg"))
            return UnOpNode(op, operand)

        elif node_type in ("identifier", "var"):
            name = payload if isinstance(payload, str) else cls._get(payload, "name", "value", "id", "var")
            name = cls._extract_name(name)
            return VarNode(name)

        elif node_type in ("const", "number"):
            val = payload if isinstance(payload, (int, float)) else cls._get(payload, "value", "val", "const")
            return ConstNode(val)

        elif node_type == "expr":
            inner = cls._get(payload, "expr", "expression", "value")
            return cls.parse(inner)

        elif node_type == "skip":
            return SkipNode()

        raise ValueError(f"Unknown AST node type: {node_type}")
