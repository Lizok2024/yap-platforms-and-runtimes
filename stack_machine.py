from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from compiler import compile_ast
from machine import StackMachine, parse_program, program_to_json, program_to_text


def _load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as source_file:
        return json.load(source_file)


def _tokens_from_value(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.split()
    if isinstance(value, list):
        return [str(token) for token in value]
    raise ValueError("Input must be a string or an array of tokens")


def _load_tokens(path: str | None) -> list[str]:
    if path is None:
        return []
    return Path(path).read_text(encoding="utf-8").split()


def _embedded_tokens(ast: Any) -> list[str]:
    if isinstance(ast, dict) and "input" in ast:
        return _tokens_from_value(ast["input"])
    return []


def _run(instructions, tokens: list[str]) -> int:
    output = StackMachine(instructions, tokens).run()
    for line in output:
        print(line)
    return 0


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile homework AST JSON to abstract-machine code and run it."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    compile_command = commands.add_parser("compile", help="compile AST JSON")
    compile_command.add_argument("ast", help="path to AST JSON")
    compile_command.add_argument("-o", "--output", help="output file (default: stdout)")
    compile_command.add_argument(
        "--format", choices=("text", "json"), default="text", help="machine-code format"
    )

    run_command = commands.add_parser("run", help="run a machine program")
    run_command.add_argument("program", help="path to machine text or JSON")
    run_command.add_argument("--input", help="file containing whitespace-separated input tokens")

    exec_command = commands.add_parser("exec", help="compile AST JSON and run it")
    exec_command.add_argument("ast", help="path to AST JSON")
    exec_command.add_argument("--input", help="input file; overrides input embedded in AST JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "compile":
            instructions = compile_ast(_load_json(args.ast))
            rendered = (
                program_to_json(instructions)
                if args.format == "json"
                else program_to_text(instructions)
            )
            if args.output:
                Path(args.output).write_text(rendered, encoding="utf-8")
            else:
                sys.stdout.write(rendered)
            return 0

        if args.command == "run":
            program_text = Path(args.program).read_text(encoding="utf-8")
            instructions = parse_program(program_text)
            return _run(instructions, _load_tokens(args.input))

        ast = _load_json(args.ast)
        tokens = _load_tokens(args.input) if args.input else _embedded_tokens(ast)
        return _run(compile_ast(ast), tokens)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
