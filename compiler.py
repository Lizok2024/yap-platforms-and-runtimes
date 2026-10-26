import argparse
import json
import sys
from pathlib import Path
from typing import Any

from ast_nodes import (
    AssignNode,
    ASTNode,
    BinOpNode,
    CompoundAssignNode,
    ConstNode,
    DoWhileNode,
    ElemNode,
    ForNode,
    IfNode,
    ReadNode,
    SeqNode,
    SexpNode,
    SkipNode,
    UnOpNode,
    VarNode,
    WhileNode,
    WriteNode,
)
from parser import ASTParser
from stack_machine import Instruction

SCRATCH = "__tmp"

_BINARY_ALIASES = {
    "+": ("+", "Plus"),
    "-": ("-", "Minus"),
    "*": ("*", "Star"),
    "/": ("/", "Slash"),
    "%": ("%", "Percent"),
    "==": ("==", "Eq", "Equal"),
    "!=": ("!=", "Ne", "NotEqual"),
    "<": ("<", "Lt"),
    "<=": ("<=", "Le"),
    ">": (">", "Gt"),
    ">=": (">=", "Ge"),
    "&&": ("&&", "and", "And", "LogicalAnd"),
    "||": ("||", "or", "Or", "LogicalOr"),
}
BINARY_OPS = {
    alias: canon for canon, aliases in _BINARY_ALIASES.items() for alias in aliases
}
NOT_OPS = {"!", "not", "Not", "LogicalNot"}
NEG_OPS = {"-", "Minus"}
POS_OPS = {"+", "Plus"}


class CompileError(ValueError):
    pass


class Compiler:
    def __init__(self) -> None:
        self.code: list[Instruction] = []
        self._label_counter = 0



    def compile(self, root: ASTNode | None) -> list[Instruction]:
        self.code = []
        self._label_counter = 0
        self.stmt(root)
        return list(self.code)



    def _emit(
        self, opcode: str, argument: str | int | tuple[str, int] | None = None
    ) -> None:
        self.code.append(Instruction(opcode, argument))

    def _label(self, hint: str) -> str:
        self._label_counter += 1
        return f"{hint}_{self._label_counter}"

    @staticmethod
    def _binary(op: Any) -> str:
        try:
            return BINARY_OPS[op]
        except (KeyError, TypeError):
            raise CompileError(f"Unknown binary operator: {op}") from None

    def _expect(self, node: ASTNode | None, what: str) -> ASTNode:
        if node is None:
            raise CompileError(f"Missing expression: {what}")
        return node



    def stmt(self, node: ASTNode | None) -> None:
        if node is None or isinstance(node, (SkipNode, ConstNode)):
            return

        if isinstance(node, SeqNode):
            for child in node.statements:
                self.stmt(child)

        elif isinstance(node, AssignNode):
            self.expr(node.expr)
            self._emit("ST", node.target)

        elif isinstance(node, CompoundAssignNode):
            self._compound_value(node)
            self._emit("ST", node.target)

        elif isinstance(node, ReadNode):
            self._emit("READ")
            self._emit("ST", node.target)

        elif isinstance(node, WriteNode):
            self.expr(node.expr)
            self._emit("WRITE")

        elif isinstance(node, WhileNode):
            start, end = self._label("while_start"), self._label("while_end")
            self._emit("LABEL", start)
            self.expr(node.cond)
            self._emit("JZ", end)
            self.stmt(node.body)
            self._emit("JMP", start)
            self._emit("LABEL", end)

        elif isinstance(node, DoWhileNode):
            start = self._label("do_start")
            self._emit("LABEL", start)
            self.stmt(node.body)
            self.expr(node.cond)
            self._emit("JNZ", start)

        elif isinstance(node, ForNode):
            start, end = self._label("for_start"), self._label("for_end")
            self.stmt(node.init)
            self._emit("LABEL", start)
            if node.cond is not None:
                self.expr(node.cond)
                self._emit("JZ", end)
            self.stmt(node.body)
            self.stmt(node.update)
            self._emit("JMP", start)
            self._emit("LABEL", end)

        elif isinstance(node, IfNode):
            end = self._label("if_end")
            if node.else_branch is None:
                self.expr(node.cond)
                self._emit("JZ", end)
                self.stmt(node.then_branch)
            else:
                else_label = self._label("if_else")
                self.expr(node.cond)
                self._emit("JZ", else_label)
                self.stmt(node.then_branch)
                self._emit("JMP", end)
                self._emit("LABEL", else_label)
                self.stmt(node.else_branch)
            self._emit("LABEL", end)

        elif isinstance(node, (VarNode, BinOpNode, UnOpNode, SexpNode, ElemNode)):


            self.expr(node)
            self._emit("ST", SCRATCH)

        else:
            raise CompileError(f"Cannot compile node: {type(node).__name__}")



    def expr(self, node: ASTNode | None) -> None:
        node = self._expect(node, "expression expected")

        if isinstance(node, ConstNode):
            self._emit("CONST", node.value)

        elif isinstance(node, VarNode):
            self._emit("LD", node.name)

        elif isinstance(node, SexpNode):
            for arg in node.args:
                self.expr(arg)
            self._emit("SEXP", (node.name, len(node.args)))

        elif isinstance(node, ElemNode):
            self.expr(node.expr)
            self.expr(node.index)
            self._emit("ELEM")

        elif isinstance(node, BinOpNode):
            if node.op in NOT_OPS and node.right is None:
                self._not(node.left)
                return
            op = self._binary(node.op)
            self.expr(node.left)
            self.expr(node.right)

            self._emit("BINOP", op)

        elif isinstance(node, UnOpNode):
            if node.op in NOT_OPS:
                self._not(node.operand)
            elif node.op in NEG_OPS:
                self._emit("CONST", 0)
                self.expr(node.operand)
                self._emit("BINOP", "-")
            elif node.op in POS_OPS:
                self.expr(node.operand)
            else:
                raise CompileError(f"Unknown unary operator: {node.op}")

        elif isinstance(node, AssignNode):
            self.expr(node.expr)
            self._emit("ST", node.target)
            self._emit("LD", node.target)

        elif isinstance(node, CompoundAssignNode):
            self._compound_value(node)
            self._emit("ST", node.target)
            self._emit("LD", node.target)

        elif isinstance(node, ReadNode):
            self._emit("READ")
            self._emit("ST", node.target)
            self._emit("LD", node.target)

        elif isinstance(node, WriteNode):
            self.expr(node.expr)
            self._emit("ST", SCRATCH)
            self._emit("LD", SCRATCH)
            self._emit("WRITE")
            self._emit("LD", SCRATCH)

        elif isinstance(node, SeqNode):
            if not node.statements:
                raise CompileError("Empty sequence used as an expression")
            for child in node.statements[:-1]:
                self.stmt(child)
            self.expr(node.statements[-1])

        else:
            raise CompileError(
                f"{type(node).__name__} has no value and cannot be used as an expression"
            )



    def _not(self, operand: ASTNode | None) -> None:

        self.expr(operand)
        self._emit("CONST", 0)
        self._emit("BINOP", "==")

    def _compound_value(self, node: CompoundAssignNode) -> None:

        op = self._binary(node.op)
        self._emit("LD", node.target)
        self.expr(node.expr)
        self._emit("BINOP", op)




def compile_ast(raw: Any) -> list[Instruction]:

    return Compiler().compile(ASTParser.parse(raw))


def compile_text(text: str) -> list[Instruction]:

    return compile_ast(json.loads(text.lstrip("\ufeff")))


def to_json(program: list[Instruction]) -> list:

    return [
        i.opcode if i.argument is None else {
            i.opcode: list(i.argument) if i.opcode == "SEXP" else i.argument
        }
        for i in program
    ]


def dumps_program(program: list[Instruction]) -> str:

    items = [json.dumps(item, ensure_ascii=False) for item in to_json(program)]
    if not items:
        return "[]"
    return "[\n  " + ",\n  ".join(items) + "\n]"


def to_asm(program: list[Instruction]) -> str:

    lines = []
    for i in program:
        lines.append(f"{i.argument}:" if i.opcode == "LABEL" else f"    {i}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Компилятор JSON-AST в инструкции стековой машины"
    )
    parser.add_argument(
        "program", type=Path, nargs="?",
        help="UTF-8 JSON-файл с AST (если не указан - читается stdin)",
    )
    parser.add_argument("-o", "--output", type=Path, help="куда записать результат")
    parser.add_argument(
        "--asm", action="store_true", help="вывести текстовый листинг вместо JSON"
    )
    args = parser.parse_args(argv)

    text = (
        args.program.read_text(encoding="utf-8-sig")
        if args.program
        else sys.stdin.read()
    )
    try:
        program = compile_text(text)
    except ValueError as error:
        print(f"Compile error: {error}", file=sys.stderr)
        return 1

    result = to_asm(program) if args.asm else dumps_program(program)
    if args.output:
        args.output.write_text(result + "\n", encoding="utf-8")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
