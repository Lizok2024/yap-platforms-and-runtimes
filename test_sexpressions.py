import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from compiler import compile_ast, to_json
from context import ExecutionContext
from interpreter import Interpreter
from stack_machine import StackMachine, parse_json_program
from tests import assign, binop, c, seq, v, write


ROOT = Path(__file__).resolve().parent


def sexp(name, *args):
    return {"sexp": name, "args": list(args)}


def elem(value, index):
    return {"elem": value, "index": index}


class SExpressionTests(unittest.TestCase):
    def assert_paths(self, ast, expected):
        output = io.StringIO()
        with redirect_stdout(output):
            interpreted = Interpreter().interpret(ast)
        self.assertEqual(output.getvalue().splitlines(), expected)

        program = parse_json_program(to_json(compile_ast(ast)))
        machine = StackMachine(program, ExecutionContext())
        output = io.StringIO()
        with redirect_stdout(output):
            machine.run(max_steps=10_000)
        self.assertEqual(output.getvalue().splitlines(), expected)
        self.assertEqual(machine.stack, [])
        variables = dict(machine.context.env.vars)
        variables.pop("__tmp", None)
        self.assertEqual(variables, interpreted.env.vars)

    def test_reference_example(self):
        # AST and machine JSON were exported by the reference website.
        ast = json.loads((ROOT / "sexpressions.json").read_text(encoding="utf-8"))
        machine_json = json.loads((ROOT / "compiled_sexpressions.json").read_text(encoding="utf-8"))
        expected = (ROOT / "sexpressions.expected.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(to_json(compile_ast(ast)), machine_json)
        self.assert_paths(ast, expected)

    def test_nullary_constructors_and_case_sensitive_list_tags(self):
        self.assert_paths(
            seq(write(sexp("Empty")), write(sexp("nil")),
                write(sexp("Cons", c(1), sexp("Nil")))),
            ["Empty", "{}", "Cons (1, Nil)"],
        )

    def test_dynamic_index_and_nested_fields(self):
        ast = seq(
            assign("x", sexp("Triple", c(10), sexp("Pair", c(20), c(30)), c(40))),
            assign("i", c(1)),
            write(elem(elem(v("x"), v("i")), binop("-", c(2), c(1)))),
            write(elem(v("x"), binop("+", v("i"), c(1)))),
        )
        self.assert_paths(ast, ["30", "40"])

    def test_typed_ast_form(self):
        expression = {
            "type": "elem", "expr": {"type": "sexp", "name": "Box", "args": [c(7)]},
            "index": c(0),
        }
        for ast in [{"write": expression}, {"type": "write", "expr": expression}]:
            with self.subTest(ast=ast):
                self.assert_paths(ast, ["7"])

    def test_improper_cons_remains_a_constructor(self):
        self.assert_paths(write(sexp("cons", c(1), c(2))), ["cons (1, 2)"])

    def test_index_errors_on_both_execution_paths(self):
        pair = sexp("Pair", c(1), c(2))
        for value, index, error in [
            (pair, c(-1), IndexError), (pair, c(2), IndexError),
            (sexp("nil"), c(0), IndexError),
            (pair, sexp("Index"), TypeError), (c(1), c(0), TypeError),
        ]:
            ast = write(elem(value, index))
            with self.subTest(value=value, index=index):
                with self.assertRaises(error):
                    Interpreter().interpret(ast)
                with self.assertRaises(error):
                    StackMachine(compile_ast(ast)).run()

    def test_constructor_fields_are_not_integer_operands(self):
        for ast in [write(binop("+", sexp("Box", c(1)), c(2))),
                    {"if": {"cond": sexp("Box"), "then": write(c(1))}}]:
            with self.subTest(ast=ast):
                with self.assertRaises(TypeError):
                    Interpreter().interpret(ast)
                with self.assertRaises(TypeError):
                    StackMachine(compile_ast(ast)).run()

    def test_invalid_ast(self):
        for ast in [
            {"sexp": "Pair", "args": 1}, {"sexp": "", "args": []},
            {"sexp": "Pair", "args": [None]}, {"sexp": 1, "args": []},
            {"elem": c(1)}, {"elem": None, "index": c(0)},
        ]:
            with self.subTest(ast=ast), self.assertRaises(ValueError):
                compile_ast(write(ast))

    def test_machine_preserves_field_order_and_stack_prefix(self):
        for instructions, expected in [
            ([{"CONST": 1}, {"CONST": 2}, {"SEXP": ["Pair", 2]}], "Pair (1, 2)"),
            ([{"SEXP": ["nil", 0]}], "{}"),
        ]:
            machine = StackMachine(parse_json_program(
                [{"CONST": 99}] + instructions + ["WRITE", "WRITE"]
            ))
            output = io.StringIO()
            with redirect_stdout(output):
                machine.run()
            self.assertEqual(output.getvalue().splitlines(), [expected, "99"])
            self.assertEqual(machine.stack, [])

    def test_invalid_machine_instructions(self):
        for raw in [
            [{"SEXP": "Pair"}], [{"SEXP": []}], [{"SEXP": ["Pair", -1]}],
            [{"SEXP": ["Pair", True]}], [{"SEXP": ["Pair", 1.5]}],
            [{"SEXP": ["", 0]}], [{"SEXP": ["Pair", 2, 3]}],
            [{"ELEM": None}], ["SEXP"],
        ]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_json_program(raw)

    def test_new_instructions_detect_underflow_before_popping(self):
        for instruction in [{"SEXP": ["Pair", 2]}, "ELEM"]:
            machine = StackMachine(parse_json_program([{"CONST": 1}, instruction]))
            with self.assertRaisesRegex(RuntimeError, "underflow"):
                machine.run()
            self.assertEqual(machine.stack, [1])

    def test_cli_compiler_and_standalone_machine(self):
        expected = (ROOT / "sexpressions.expected.txt").read_text(encoding="utf-8")
        direct = subprocess.run(
            [sys.executable, "interpreter.py", "sexpressions.json"],
            text=True, capture_output=True, cwd=ROOT,
        )
        self.assertEqual(direct.returncode, 0, direct.stderr)
        self.assertEqual(direct.stdout, expected)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sexpressions.machine.json"
            compiled = subprocess.run(
                [sys.executable, "compiler.py", "sexpressions.json", "-o", str(output)],
                text=True, capture_output=True, cwd=ROOT,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            executed = subprocess.run(
                [sys.executable, "stack_machine.py", str(output)],
                input="", text=True, capture_output=True, cwd=ROOT,
            )
            self.assertEqual(executed.returncode, 0, executed.stderr)
            self.assertEqual(executed.stdout, expected)


if __name__ == "__main__":
    unittest.main()
