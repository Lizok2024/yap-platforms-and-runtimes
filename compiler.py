from __future__ import annotations

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
from machine import Instruction
from parser import ASTParser


class CompileError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

class Compiler:
    def __init__(self) -> None:
        self.instructions: list[Instruction] = []
        self._label_index = 0

    def compile(self, root: ASTNode | None) -> list[Instruction]:
        self.instructions = []
        self._label_index = 0
        if root is not None:
            self._compile_statement(root)
        return list(self.instructions)

    def _emit(self, opcode: str, argument: str | int | None = None) -> None:
        self.instructions.append(Instruction(opcode, argument))

    def _new_label(self) -> str:
        label = f"L{self._label_index}"
        self._label_index += 1
        return label

    def _compile_statement(self, node: ASTNode) -> None:
        if isinstance(node, SkipNode):
            return
        if isinstance(node, SeqNode):
            for statement in node.statements:
                self._compile_statement(statement)
            return
        if isinstance(node, AssignNode):
            self._compile_expression(node.expr)
            self._emit("ST", node.target)
            return
        if isinstance(node, CompoundAssignNode):
            self._emit("LD", node.target)
            self._compile_expression(node.expr)
            self._emit("BINOP", node.op)
            self._emit("ST", node.target)
            return
        if isinstance(node, ReadNode):
            self._emit("READ")
            self._emit("ST", node.target)
            return
        if isinstance(node, WriteNode):
            self._compile_expression(node.expr)
            self._emit("WRITE")
            return
        if isinstance(node, IfNode):
            self._compile_if(node)
            return
        if isinstance(node, WhileNode):
            self._compile_while(node)
            return
        if isinstance(node, DoWhileNode):
            self._compile_do_while(node)
            return
        if isinstance(node, ForNode):
            self._compile_for(node)
            return
        raise CompileError(f"Unsupported statement node: {type(node).__name__}")

    def _compile_expression(self, node: ASTNode | None) -> None:
        if isinstance(node, ConstNode):
            self._emit("CONST", node.value)
            return
        if isinstance(node, VarNode):
            self._emit("LD", node.name)
            return
        if isinstance(node, BinOpNode):
            if node.op in ("!", "not", "Not", "LogicalNot") and node.right is None:
                self._compile_expression(node.left)
                self._emit("CONST", 0)
                self._emit("BINOP", "==")
                return
            if node.left is None or node.right is None:
                raise CompileError(f"Binary operator {node.op!r} needs two operands")
            self._compile_expression(node.left)
            self._compile_expression(node.right)
            self._emit("BINOP", node.op)
            return
        if isinstance(node, UnOpNode):
            if node.op in ("!", "not", "Not", "LogicalNot"):
                self._compile_expression(node.operand)
                self._emit("CONST", 0)
                self._emit("BINOP", "==")
                return
            if node.op in ("-", "Minus"):
                self._emit("CONST", 0)
                self._compile_expression(node.operand)
                self._emit("BINOP", "-")
                return
            if node.op in ("+", "Plus"):
                self._compile_expression(node.operand)
                return
            raise CompileError(f"Unsupported unary operator: {node.op!r}")
        raise CompileError(
            f"Unsupported expression node: {type(node).__name__ if node is not None else 'None'}"
        )

    def _compile_if(self, node: IfNode) -> None:
        else_label = self._new_label()
        self._compile_expression(node.cond)
        self._emit("JZ", else_label)
        if node.then_branch is not None:
            self._compile_statement(node.then_branch)

        if node.else_branch is None:
            self._emit("LABEL", else_label)
            return

        end_label = self._new_label()
        self._emit("JMP", end_label)
        self._emit("LABEL", else_label)
        self._compile_statement(node.else_branch)
        self._emit("LABEL", end_label)

    def _compile_while(self, node: WhileNode) -> None:
        start_label = self._new_label()
        end_label = self._new_label()
        self._emit("LABEL", start_label)
        self._compile_expression(node.cond)
        self._emit("JZ", end_label)
        if node.body is not None:
            self._compile_statement(node.body)
        self._emit("JMP", start_label)
        self._emit("LABEL", end_label)

    def _compile_do_while(self, node: DoWhileNode) -> None:
        start_label = self._new_label()
        self._emit("LABEL", start_label)
        if node.body is not None:
            self._compile_statement(node.body)
        self._compile_expression(node.cond)
        self._emit("JNZ", start_label)

    def _compile_for(self, node: ForNode) -> None:
        if node.init is not None:
            self._compile_statement(node.init)

        start_label = self._new_label()
        end_label = self._new_label() if node.cond is not None else None
        self._emit("LABEL", start_label)
        if node.cond is not None:
            self._compile_expression(node.cond)
            self._emit("JZ", end_label)
        if node.body is not None:
            self._compile_statement(node.body)
        if node.update is not None:
            self._compile_statement(node.update)
        self._emit("JMP", start_label)
        if end_label is not None:
            self._emit("LABEL", end_label)


def compile_ast(raw_ast: object) -> list[Instruction]:
    root = ASTParser.parse(raw_ast)
    return Compiler().compile(root)
