import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys

from ast_nodes import BinOpNode
from context import ExecutionContext
from runtime_values import SExpression, Value, get_element, require_int


OPERATORS = {
    "+", "Plus", "-", "Minus", "*", "Star", "/", "Slash", "%", "Percent",
    "==", "Eq", "Equal", "!=", "Ne", "NotEqual", "<", "Lt", "<=", "Le",
    ">", "Gt", ">=", "Ge", "&&", "and", "And", "LogicalAnd",
    "||", "or", "Or", "LogicalOr",
}
NO_ARGUMENT_OPCODES = {"READ", "WRITE", "ELEM"}
OPCODES = NO_ARGUMENT_OPCODES | {"LD", "ST", "CONST", "BINOP", "LABEL", "JMP", "JZ", "JNZ", "SEXP"}
JUMPS = {"JMP", "JZ", "JNZ"}


@dataclass(frozen=True)
class Instruction:
    opcode: str
    argument: str | int | tuple[str, int] | None = None

    def __post_init__(self):
        if self.opcode not in OPCODES:
            raise ValueError(f"Unknown instruction: {self.opcode}")
        if self.opcode in NO_ARGUMENT_OPCODES:
            if self.argument is not None:
                raise ValueError(f"{self.opcode} takes no argument")
        elif self.opcode == "CONST":
            if type(self.argument) is not int:
                raise ValueError("CONST requires an integer")
        elif self.opcode == "SEXP":
            if not isinstance(self.argument, (list, tuple)) or len(self.argument) != 2:
                raise ValueError("SEXP requires [constructor, arity]")
            name, arity = self.argument
            SExpression(name)
            if type(arity) is not int or arity < 0:
                raise ValueError("SEXP arity must be a nonnegative integer")
            object.__setattr__(self, "argument", (name, arity))
        elif not isinstance(self.argument, str) or not self.argument or any(
            c.isspace() for c in self.argument
        ):
            raise ValueError(f"{self.opcode} requires one nonempty token")
        if self.opcode == "BINOP" and self.argument not in OPERATORS:
            raise ValueError(f"Unknown binary operator: {self.argument}")

    def __str__(self):
        if self.opcode == "SEXP":
            name, arity = self.argument
            return f"SEXP {json.dumps(name, ensure_ascii=False)} {arity}"
        return self.opcode if self.argument is None else f"{self.opcode} {self.argument}"


def parse_program(text: str) -> list[Instruction]:
    """Parse a JSON array of machine instructions."""
    return parse_json_program(json.loads(text.lstrip("\ufeff")))


def parse_json_program(raw) -> list[Instruction]:
    """Website format: [\"READ\", {\"CONST\": 3}, ..., \"WRITE\"]."""
    if not isinstance(raw, list):
        raise ValueError("Machine JSON must be an array of instructions")
    program = []
    for index, item in enumerate(raw):
        try:
            if isinstance(item, str) and item in NO_ARGUMENT_OPCODES:
                instruction = Instruction(item)
            elif isinstance(item, dict) and len(item) == 1:
                opcode, argument = next(iter(item.items()))
                if opcode in NO_ARGUMENT_OPCODES:
                    raise ValueError(f"{opcode} must be a string")
                instruction = Instruction(opcode, argument)
            else:
                raise ValueError("Expected an instruction string or a single-key instruction object")
            program.append(instruction)
        except ValueError as error:
            raise ValueError(f"Instruction {index}: {error}") from error
    return program


class StackMachine:
    def __init__(self, program: list[Instruction], context: ExecutionContext | None = None):
        self.program = list(program)
        self.context = context if context is not None else ExecutionContext()
        self.stack: list[Value] = []
        self.pc = 0
        self.labels = {}
        for index, instruction in enumerate(self.program):
            if instruction.opcode == "LABEL":
                if instruction.argument in self.labels:
                    raise ValueError(f"Duplicate label: {instruction.argument}")
                self.labels[instruction.argument] = index
        for instruction in self.program:
            if instruction.opcode in JUMPS and instruction.argument not in self.labels:
                raise ValueError(f"Undefined label: {instruction.argument}")

    def run(self, max_steps: int | None = None) -> ExecutionContext:
        """Run from the current PC. An optional budget bounds infinite programs."""
        if max_steps is not None and max_steps < 0:
            raise ValueError("max_steps must be nonnegative")
        steps = 0
        while self.pc < len(self.program):
            if max_steps is not None and steps >= max_steps:
                raise RuntimeError(f"Instruction limit exceeded: {max_steps}")
            instruction = self.program[self.pc]
            op, arg = instruction.opcode, instruction.argument
            required = 2 if op in {"BINOP", "ELEM"} else int(op in {"WRITE", "ST", "JZ", "JNZ"})
            if op == "SEXP":
                required = arg[1]
            if len(self.stack) < required:
                raise RuntimeError(f"Stack underflow at instruction {self.pc}: {instruction}")
            next_pc = self.pc + 1
            if op == "READ":
                self.stack.append(self.context.read_int())
            elif op == "WRITE":
                self.context.write(self.stack.pop())
            elif op == "CONST":
                self.stack.append(arg)
            elif op == "LD":
                self.stack.append(self.context.env.get(arg))
            elif op == "ST":
                self.context.env.set(arg, self.stack.pop())
            elif op == "BINOP":
                right = self.stack.pop()
                left = self.stack.pop()
                self.stack.append(BinOpNode._apply_op(arg, left, right))
            elif op == "SEXP":
                name, arity = arg
                fields = tuple(self.stack[-arity:]) if arity else ()
                if arity:
                    del self.stack[-arity:]
                self.stack.append(SExpression(name, fields))
            elif op == "ELEM":
                index = self.stack.pop()
                value = self.stack.pop()
                self.stack.append(get_element(value, index))
            elif op == "JMP":
                next_pc = self.labels[arg]
            elif op in {"JZ", "JNZ"}:
                value = require_int(self.stack.pop())
                if (value == 0) == (op == "JZ"):
                    next_pc = self.labels[arg]
            self.pc = next_pc
            steps += 1
        return self.context


def main():
    parser = argparse.ArgumentParser(description="Execute stack-machine instructions")
    parser.add_argument("program", type=Path, help="UTF-8 JSON instruction file")
    parser.add_argument("--max-steps", type=int, default=None)
    args = parser.parse_args()
    try:
        program = parse_program(args.program.read_text(encoding="utf-8-sig"))
        StackMachine(program, ExecutionContext(sys.stdin.read().split())).run(args.max_steps)
    except (OSError, ValueError, TypeError, IndexError, RuntimeError, EOFError, NameError, ArithmeticError) as error:
        print(f"Machine error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
