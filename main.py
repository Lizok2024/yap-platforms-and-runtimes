import json
import sys

from context import ExecutionContext
from parser import ASTParser


def main():
    data = sys.stdin.read()
    if not data.strip():
        return

    ast_raw = json.loads(data)

    tokens = []
    if isinstance(ast_raw, dict) and "input" in ast_raw:
        inp = ast_raw["input"]
        if isinstance(inp, str):
            tokens = inp.split()
        elif isinstance(inp, list):
            tokens = [str(x) for x in inp]

    context = ExecutionContext(tokens)
    root_node = ASTParser.parse(ast_raw)

    if root_node:
        root_node.eval(context)

if __name__ == "__main__":
    main()
