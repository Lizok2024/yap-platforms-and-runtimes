import io
import os
import sys
from contextlib import redirect_stdout

from context import ExecutionContext
from parser import ASTParser


def run_ast(ast, input_tokens=None):
    ctx = ExecutionContext(list(input_tokens or []))
    buf = io.StringIO()
    with redirect_stdout(buf):
        root = ASTParser.parse(ast)
        if root is not None:
            root.eval(ctx)
    text = buf.getvalue()
    if not text:
        return []
    return text.rstrip("\n").split("\n")


TESTS = []


def case(name, ast, expected, input_tokens=None):
    TESTS.append((name, ast, input_tokens, expected))


def c(v):
    return {"const": v}


def v(name):
    return {"var": name}


def binop(op, left, right):
    return {"binop": op, "left": left, "right": right}


def assign(dst, src):
    return {"assn": {"dst": dst, "src": src}}


def compound(dst, op, src):
    return {"compoundassign": {"dst": dst, "op": op, "src": src}}


def seq(*items):
    result = items[-1]
    for item in reversed(items[:-1]):
        result = {"seq": {"left": item, "right": result}}
    return result


def write(expr):
    return {"write": expr}


def read(name):
    return {"read": name}


def block(*items):
    return seq(*items)


def skip():
    return {"skip": True}


case(
    "write const",
    write(c(42)),
    ["42"],
)

case(
    "write add",
    write(binop("+", c(1), c(2))),
    ["3"],
)

case(
    "write sub",
    write(binop("-", c(10), c(3))),
    ["7"],
)

case(
    "write mul",
    write(binop("*", c(4), c(5))),
    ["20"],
)

case(
    "write div",
    write(binop("/", c(7), c(2))),
    ["3"],
)

case(
    "write mod",
    write(binop("%", c(7), c(3))),
    ["1"],
)

case(
    "eq true",
    write(binop("==", c(3), c(3))),
    ["1"],
)

case(
    "eq false",
    write(binop("==", c(3), c(4))),
    ["0"],
)

case(
    "ne",
    write(binop("!=", c(3), c(4))),
    ["1"],
)

case(
    "lt",
    write(binop("<", c(2), c(3))),
    ["1"],
)

case(
    "le equal",
    write(binop("<=", c(3), c(3))),
    ["1"],
)

case(
    "gt",
    write(binop(">", c(2), c(3))),
    ["0"],
)

case(
    "ge equal",
    write(binop(">=", c(3), c(3))),
    ["1"],
)

case(
    "and true",
    write(binop("&&", c(1), c(1))),
    ["1"],
)

case(
    "and false",
    write(binop("&&", c(1), c(0))),
    ["0"],
)

case(
    "or true",
    write(binop("||", c(0), c(1))),
    ["1"],
)

case(
    "or false",
    write(binop("||", c(0), c(0))),
    ["0"],
)

case(
    "not zero",
    write({"binop": "!", "left": c(0), "right": None}),
    ["1"],
)

case(
    "not nonzero",
    write({"binop": "!", "left": c(5), "right": None}),
    ["0"],
)

case(
    "assign and write",
    seq(assign("x", c(5)), write(v("x"))),
    ["5"],
)

case(
    "compound plus",
    seq(assign("x", c(5)), compound("x", "+", c(3)), write(v("x"))),
    ["8"],
)

case(
    "compound minus",
    seq(assign("x", c(5)), compound("x", "-", c(2)), write(v("x"))),
    ["3"],
)

case(
    "compound mul",
    seq(assign("x", c(5)), compound("x", "*", c(2)), write(v("x"))),
    ["10"],
)

case(
    "if true then",
    {"if": {"cond": c(1), "then": write(c(1))}},
    ["1"],
)

case(
    "if false no else",
    {"if": {"cond": c(0), "then": write(c(1))}},
    [],
)

case(
    "if else",
    {"if": {"cond": c(0), "then": write(c(1)), "else": write(c(2))}},
    ["2"],
)

case(
    "if elif else first",
    {
        "if": {
            "cond": c(1),
            "then": write(c(10)),
            "else": {
                "if": {
                    "cond": c(1),
                    "then": write(c(20)),
                    "else": write(c(30)),
                }
            },
        }
    },
    ["10"],
)

case(
    "if elif else second",
    {
        "if": {
            "cond": c(0),
            "then": write(c(10)),
            "else": {
                "if": {
                    "cond": c(1),
                    "then": write(c(20)),
                    "else": write(c(30)),
                }
            },
        }
    },
    ["20"],
)

case(
    "if elif else third",
    {
        "if": {
            "cond": c(0),
            "then": write(c(10)),
            "else": {
                "if": {
                    "cond": c(0),
                    "then": write(c(20)),
                    "else": write(c(30)),
                }
            },
        }
    },
    ["30"],
)

case(
    "while counts",
    seq(
        assign("x", c(0)),
        {
            "while": {
                "cond": binop("<", v("x"), c(3)),
                "body": seq(
                    write(v("x")),
                    compound("x", "+", c(1)),
                ),
            }
        },
    ),
    ["0", "1", "2"],
)

case(
    "do while runs once",
    seq(
        assign("x", c(5)),
        {
            "dowhile": {
                "body": seq(write(v("x")), compound("x", "+", c(1))),
                "cond": binop("<", v("x"), c(3)),
            }
        },
    ),
    ["5"],
)

case(
    "for counts",
    {
        "for": {
            "init": assign("x", c(0)),
            "cond": binop("<", v("x"), c(3)),
            "update": compound("x", "+", c(1)),
            "body": write(v("x")),
        }
    },
    ["0", "1", "2"],
)

case(
    "for sums",
    seq(
        assign("s", c(0)),
        {
            "for": {
                "init": assign("i", c(1)),
                "cond": binop("<=", v("i"), c(5)),
                "update": compound("i", "+", c(1)),
                "body": compound("s", "+", v("i")),
            }
        },
        write(v("s")),
    ),
    ["15"],
)

case(
    "skip alone",
    skip(),
    [],
)

case(
    "skip in block",
    block(skip(), write(c(7))),
    ["7"],
)

case(
    "read then write",
    seq(read("n"), write(v("n"))),
    ["5"],
    input_tokens=["5"],
)

case(
    "read twice add",
    seq(read("a"), read("b"), write(binop("+", v("a"), v("b")))),
    ["12"],
    input_tokens=["5", "7"],
)

case(
    "nested arithmetic",
    write(
        binop(
            "+",
            binop("*", c(2), c(3)),
            binop("-", c(10), c(4)),
        )
    ),
    ["12"],
)


def run_file_if_exists(path):
    if not os.path.exists(path):
        return None
    import json

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    tokens = []
    if isinstance(data, dict) and "input" in data:
        inp = data["input"]
        if isinstance(inp, str):
            tokens = inp.split()
        elif isinstance(inp, list):
            tokens = [str(x) for x in inp]
    return run_ast(data, tokens)


def run_all():
    passed = 0
    failed = 0
    failures = []

    for name, ast, input_tokens, expected in TESTS:
        try:
            got = run_ast(ast, input_tokens)
        except Exception as e:
            got = "EXC: " + type(e).__name__ + ": " + str(e)
        if got == expected:
            passed += 1
            print("PASS  " + name)
        else:
            failed += 1
            print("FAIL  " + name)
            print("      expected: " + repr(expected))
            print("      got:      " + repr(got))
            failures.append(name)

    print()
    print("program.json:")
    try:
        got = run_file_if_exists("program.json")
        if got is None:
            print("  SKIP  program.json not found")
        elif got == ["120"]:
            passed += 1
            print("  PASS  factorial(5) = 120")
        else:
            failed += 1
            print("  FAIL  expected ['120'], got " + repr(got))
            failures.append("program.json")
    except Exception as e:
        failed += 1
        print("  FAIL  exception: " + type(e).__name__ + ": " + str(e))
        failures.append("program.json")

    print()
    print("=" * 40)
    print("passed: " + str(passed))
    print("failed: " + str(failed))
    if failures:
        print("failed tests:")
        for f in failures:
            print("  - " + f)
    return failed == 0


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)