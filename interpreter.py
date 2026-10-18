import argparse
import json
import sys
from numbers import Real
from pathlib import Path
from typing import Any

from context import ExecutionContext
from parser import ASTParser


class Interpreter:
    def interpret(self, raw_program: Any) -> ExecutionContext:
        input_tokens = []
        if isinstance(raw_program, dict) and "input" in raw_program:
            program_input = raw_program["input"]
            if isinstance(program_input, str):
                input_tokens = program_input.split()
            elif isinstance(program_input, list):
                input_tokens = [str(value) for value in program_input]

        context = ExecutionContext(input_tokens)
        root = ASTParser.parse(raw_program)
        if root is not None:
            root.eval(context)
        return context

    def interpret_text(self, source: str) -> ExecutionContext:
        return self.interpret(json.loads(source.lstrip("\ufeff")))

    @staticmethod
    def sum_arrays(arrays: Any) -> int | float:
        if not isinstance(arrays, (list, tuple)):
            raise TypeError("Expected an array of numbers or nested arrays")

        total: int | float = 0
        pending = list(arrays)

        while pending:
            value = pending.pop()
            if isinstance(value, (list, tuple)):
                pending.extend(value)
            elif isinstance(value, Real) and not isinstance(value, bool):
                total += value
            else:
                raise TypeError(f"Expected a number or nested array, got {type(value).__name__}")

        return total


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interpret JSON AST programs")
    parser.add_argument("program", type=Path, nargs="?", help="JSON file; stdin is used if omitted")
    parser.add_argument("--sum-arrays", action="store_true", help="Sum all numbers in a JSON array, including nested arrays")
    args = parser.parse_args(argv)

    try:
        source = args.program.read_text(encoding="utf-8-sig") if args.program else sys.stdin.read()
        if not source.strip():
            return 0
        if args.sum_arrays:
            print(Interpreter.sum_arrays(json.loads(source)))
        else:
            Interpreter().interpret_text(source)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, EOFError, NameError, RuntimeError) as error:
        print(f"Interpreter error: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
