from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from ast_nodes import BinOpNode
from environment import Environment


class MachineError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)

@dataclass(frozen=True)
class Instruction:
    opcode: str
    argument: str | int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.opcode, str):
            raise ValueError("Instruction opcode must be a string")
        opcode = self.opcode.upper()
        object.__setattr__(self, "opcode", opcode)
        if opcode not in {"READ", "WRITE", "LD", "ST", "CONST", "BINOP", "LABEL", "JMP", "JZ", "JNZ"}:
            raise ValueError(f"Unknown instruction: {self.opcode}")
        if opcode in {"READ", "WRITE"}:
            if self.argument is not None:
                raise ValueError(f"{opcode} does not take an argument")
        elif opcode == "CONST":
            if not isinstance(self.argument, int) or isinstance(self.argument, bool):
                raise ValueError("CONST expects an integer argument")
        elif not isinstance(self.argument, str) or not self.argument:
            raise ValueError(f"{opcode} expects a non-empty string argument")

    def to_dict(self) -> dict[str, Any]:
        return {"opcode": self.opcode, "argument": self.argument}

    def to_text(self) -> str:
        if self.argument is None:
            return self.opcode
        return f"{self.opcode} {self.argument}"


def program_to_text(instructions: Iterable[Instruction]) -> str:
    lines = [instruction.to_text() for instruction in instructions]
    return "\n".join(lines) + ("\n" if lines else "")


def program_to_json(instructions: Iterable[Instruction]) -> str:
    return json.dumps(
        [instruction.to_dict() for instruction in instructions],
        ensure_ascii=False,
        indent=2,
    ) + "\n"


def _instruction_from_dict(data: Any, index: int) -> Instruction:
    if not isinstance(data, dict):
        raise ValueError(f"Instruction {index} must be a JSON object")
    opcode = data.get("opcode", data.get("op"))
    if not isinstance(opcode, str):
        raise ValueError(f"Instruction {index} needs a string opcode")
    argument = data.get("argument", data.get("arg"))
    try:
        return Instruction(opcode, argument)
    except ValueError as exc:
        raise ValueError(f"Invalid instruction {index}: {exc}") from exc


def program_from_json(data: Any) -> list[Instruction]:
    if isinstance(data, dict):
        data = data.get("instructions")
    if not isinstance(data, list):
        raise ValueError("Machine JSON must be an array or an object with 'instructions'")
    return [_instruction_from_dict(item, index) for index, item in enumerate(data, 1)]


def program_from_text(source: str) -> list[Instruction]:
    instructions: list[Instruction] = []
    no_argument_ops = {"READ", "WRITE"}
    integer_ops = {"CONST"}
    string_ops = {"LD", "ST", "BINOP", "LABEL", "JMP", "JZ", "JNZ"}

    for line_number, original_line in enumerate(source.splitlines(), 1):
        line = original_line.partition("#")[0].strip()
        if not line:
            continue
        parts = line.split()
        opcode = parts[0].upper()
        try:
            if opcode in no_argument_ops:
                if len(parts) != 1:
                    raise ValueError(f"{opcode} does not take an argument")
                instruction = Instruction(opcode)
            elif opcode in integer_ops:
                if len(parts) != 2:
                    raise ValueError("CONST expects one integer argument")
                instruction = Instruction(opcode, int(parts[1], 10))
            elif opcode in string_ops:
                if len(parts) != 2:
                    raise ValueError(f"{opcode} expects one argument")
                instruction = Instruction(opcode, parts[1])
            else:
                raise ValueError(f"Unknown instruction: {parts[0]}")
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: {exc}") from exc
        instructions.append(instruction)
    return instructions


def parse_program(source: str) -> list[Instruction]:
    stripped = source.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            return program_from_json(json.loads(source))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid machine JSON: {exc}") from exc
    return program_from_text(source)


class StackMachine:
    def __init__(
        self,
        instructions: Iterable[Instruction],
        input_tokens: Iterable[str | int] | None = None,
        max_steps: int | None = None,
    ) -> None:
        self.instructions = list(instructions)
        self.input_tokens = [str(token) for token in (input_tokens or [])]
        self.input_position = 0
        self.environment = Environment()
        self.stack: list[int] = []
        self.output: list[str] = []
        self.pc = 0
        self.max_steps = max_steps
        self.steps = 0
        self.labels: dict[str, int] = {}
        self._collect_labels()

    def _collect_labels(self) -> None:
        for index, instruction in enumerate(self.instructions):
            if instruction.opcode == "LABEL":
                label = str(instruction.argument)
                if label in self.labels:
                    raise MachineError(f"Duplicate label: {label}")
                self.labels[label] = index + 1
        for instruction in self.instructions:
            if instruction.opcode in {"JMP", "JZ", "JNZ"}:
                label = str(instruction.argument)
                if label not in self.labels:
                    raise MachineError(f"Unknown label: {label}")

    def _pop(self, instruction: Instruction) -> int:
        if not self.stack:
            raise MachineError(
                f"Stack underflow at instruction {self.pc + 1} ({instruction.to_text()})"
            )
        return self.stack.pop()

    def _read(self) -> int:
        if self.input_position >= len(self.input_tokens):
            raise EOFError("No input available for READ instruction")
        token = self.input_tokens[self.input_position]
        self.input_position += 1
        try:
            return int(token)
        except ValueError as exc:
            raise ValueError(f"READ expected an integer, got {token!r}") from exc

    def run(self) -> list[str]:
        while self.pc < len(self.instructions):
            if self.max_steps is not None and self.steps >= self.max_steps:
                raise MachineError(f"Instruction limit exceeded ({self.max_steps})")
            instruction = self.instructions[self.pc]
            self.steps += 1
            next_pc = self.pc + 1
            opcode = instruction.opcode
            argument = instruction.argument

            if opcode == "READ":
                self.stack.append(self._read())
            elif opcode == "WRITE":
                self.output.append(str(self._pop(instruction)))
            elif opcode == "CONST":
                self.stack.append(int(argument))
            elif opcode == "LD":
                self.stack.append(self.environment.get(str(argument)))
            elif opcode == "ST":
                self.environment.set(str(argument), self._pop(instruction))
            elif opcode == "BINOP":
                right = self._pop(instruction)
                left = self._pop(instruction)
                self.stack.append(BinOpNode._apply_op(str(argument), left, right))
            elif opcode == "LABEL":
                pass
            elif opcode == "JMP":
                next_pc = self.labels[str(argument)]
            elif opcode in {"JZ", "JNZ"}:
                value = self._pop(instruction)
                should_jump = value == 0 if opcode == "JZ" else value != 0
                if should_jump:
                    next_pc = self.labels[str(argument)]
            else:
                raise MachineError(f"Unsupported instruction: {opcode}")

            self.pc = next_pc
        return list(self.output)
