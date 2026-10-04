import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import tests as ast_tests
from compiler import CompileError, compile_ast, compile_text, to_asm, to_json
from context import ExecutionContext
from stack_machine import StackMachine, parse_json_program
from tests import assign, binop, c, compound, read, seq, skip, v, write

ROOT = Path(__file__).resolve().parent


def run_machine(program, tokens=None, max_steps=100_000):

    machine = StackMachine(program, ExecutionContext(list(tokens or [])))
    buf = io.StringIO()
    with redirect_stdout(buf):
        machine.run(max_steps)
    out = buf.getvalue()
    return (out.rstrip("\n").split("\n") if out else []), machine


def run_both(ast, tokens=None):

    expected = ast_tests.run_ast(ast, tokens)
    got, machine = run_machine(compile_ast(ast), tokens)
    return expected, got, machine


def unary(op, operand):
    return {"unary": {"op": op, "operand": operand}}


class ShapeTests(unittest.TestCase):
    def test_write_const(self):
        self.assertEqual(to_json(compile_ast(write(c(42)))), [{"CONST": 42}, "WRITE"])

    def test_read_assign(self):
        ast = seq(read("n"), assign("x", binop("+", v("n"), c(1))))
        self.assertEqual(
            to_json(compile_ast(ast)),
            ["READ", {"ST": "n"}, {"LD": "n"}, {"CONST": 1}, {"BINOP": "+"}, {"ST": "x"}],
        )

    def test_not_is_compare_with_zero(self):
        ast = write({"binop": "!", "left": c(5), "right": None})
        self.assertEqual(
            to_json(compile_ast(ast)),
            [{"CONST": 5}, {"CONST": 0}, {"BINOP": "=="}, "WRITE"],
        )

    def test_operator_aliases_are_normalized(self):
        program = compile_ast(write(binop("Plus", c(1), c(2))))
        self.assertEqual(to_json(program)[2], {"BINOP": "+"})

    def test_while_layout(self):
        ast = {"while": {"cond": v("n"), "body": write(c(1))}}
        program = compile_ast(ast)
        self.assertEqual(
            [i.opcode for i in program],
            ["LABEL", "LD", "JZ", "CONST", "WRITE", "JMP", "LABEL"],
        )
        self.assertEqual(program[0].argument, program[5].argument)
        self.assertEqual(program[2].argument, program[6].argument)

    def test_empty_programs(self):
        self.assertEqual(compile_ast(None), [])
        self.assertEqual(compile_ast([]), [])
        self.assertEqual(compile_ast(skip()), [])

    def test_json_round_trip(self):
        data = json.loads((ROOT / "program.json").read_text(encoding="utf-8"))
        program = compile_ast(data)
        self.assertEqual(parse_json_program(to_json(program)), program)

    def test_asm_listing(self):
        asm = to_asm(compile_ast({"while": {"cond": v("n"), "body": write(c(1))}}))
        self.assertIn("while_start_1:", asm)
        self.assertIn("    JZ while_end_2", asm)


class SemanticsTests(unittest.TestCase):
    def test_matches_interpreter_on_all_cases(self):
        for name, ast, tokens, expected in ast_tests.TESTS:
            with self.subTest(name=name):
                interpreted, got, machine = run_both(ast, tokens)
                self.assertEqual(interpreted, expected)
                self.assertEqual(got, expected)
                self.assertEqual(machine.stack, [])

    def test_program_json_factorial(self):
        data = json.loads((ROOT / "program.json").read_text(encoding="utf-8"))
        got, machine = run_machine(compile_ast(data), str(data["input"]).split())
        self.assertEqual(got, ["120"])
        self.assertEqual(machine.stack, [])

    def test_factorial_for_several_inputs(self):
        data = json.loads((ROOT / "program.json").read_text(encoding="utf-8"))
        program = compile_ast(data)
        for n, expected in [(0, "1"), (1, "1"), (5, "120"), (6, "720")]:
            with self.subTest(n=n):
                self.assertEqual(run_machine(program, [str(n)])[0], [expected])

    def test_assign_inside_expression(self):
        ast = seq(write(binop("+", assign("y", c(3)), c(1))), write(v("y")))
        interpreted, got, _ = run_both(ast)
        self.assertEqual(got, ["4", "3"])
        self.assertEqual(got, interpreted)

    def test_write_inside_expression(self):
        interpreted, got, machine = run_both(write(write(c(5))))
        self.assertEqual(got, ["5", "5"])
        self.assertEqual(got, interpreted)
        self.assertEqual(machine.stack, [])

    def test_compound_and_read_inside_expression(self):
        ast = seq(assign("x", c(5)), write(compound("x", "*", c(2))),
                  write(binop("+", read("a"), c(1))), write(v("a")))
        interpreted, got, _ = run_both(ast, ["4"])
        self.assertEqual(got, ["10", "5", "4"])
        self.assertEqual(got, interpreted)

    def test_sequence_inside_expression(self):
        ast = write(binop("+", seq(assign("a", c(2)), v("a")), c(1)))
        interpreted, got, _ = run_both(ast)
        self.assertEqual(got, ["3"])
        self.assertEqual(got, interpreted)

    def test_unary_operators(self):
        for op, operand, expected in [("-", 5, "-5"), ("Minus", 5, "-5"), ("+", 5, "5"),
                                      ("!", 0, "1"), ("Not", 7, "0")]:
            with self.subTest(op=op):
                interpreted, got, _ = run_both(write(unary(op, c(operand))))
                self.assertEqual(got, [expected])
                self.assertEqual(got, interpreted)

    def test_operator_aliases_run(self):
        for op in ["Plus", "Minus", "Star", "Eq", "Ne", "Lt", "Le", "Gt", "Ge", "And", "Or"]:
            with self.subTest(op=op):
                interpreted, got, _ = run_both(write(binop(op, c(6), c(3))))
                self.assertEqual(got, interpreted)

    def test_nested_loops_have_unique_labels(self):
        ast = seq(
            assign("s", c(0)),
            {"for": {
                "init": assign("i", c(1)), "cond": binop("<=", v("i"), c(3)),
                "update": compound("i", "+", c(1)),
                "body": {"for": {
                    "init": assign("j", c(1)), "cond": binop("<=", v("j"), c(3)),
                    "update": compound("j", "+", c(1)),
                    "body": compound("s", "+", binop("*", v("i"), v("j"))),
                }},
            }},
            write(v("s")),
        )
        program = compile_ast(ast)
        labels = [i.argument for i in program if i.opcode == "LABEL"]
        self.assertEqual(len(labels), len(set(labels)))
        interpreted, got, _ = run_both(ast)
        self.assertEqual(got, ["36"])
        self.assertEqual(got, interpreted)

    def test_pure_expression_statement_is_discarded(self):
        ast = seq(assign("x", c(1)), binop("+", v("x"), c(2)), v("x"), c(9), write(c(7)))
        interpreted, got, machine = run_both(ast)
        self.assertEqual(got, ["7"])
        self.assertEqual(machine.stack, [])

    def test_expression_statement_errors_are_preserved(self):
        ast = seq(binop("/", c(1), c(0)), write(c(1)))
        with self.assertRaises(ZeroDivisionError):
            ast_tests.run_ast(ast)
        with self.assertRaises(ZeroDivisionError):
            run_machine(compile_ast(ast))

    def test_no_short_circuit_like_interpreter(self):
        ast = write(binop("&&", c(0), binop("/", c(1), c(0))))
        with self.assertRaises(ZeroDivisionError):
            ast_tests.run_ast(ast)
        with self.assertRaises(ZeroDivisionError):
            run_machine(compile_ast(ast))

    def test_if_inside_loop(self):
        ast = seq(
            assign("i", c(0)),
            {"while": {"cond": binop("<", v("i"), c(5)), "body": seq(
                {"if": {"cond": binop("==", binop("%", v("i"), c(2)), c(0)),
                        "then": write(v("i")), "else": write(unary("-", v("i")))}},
                compound("i", "+", c(1)),
            )}},
        )
        interpreted, got, _ = run_both(ast)
        self.assertEqual(got, ["0", "-1", "2", "-3", "4"])
        self.assertEqual(got, interpreted)


class ErrorTests(unittest.TestCase):
    def test_unknown_binary_operator(self):
        with self.assertRaises(CompileError):
            compile_ast(write(binop("^", c(1), c(2))))

    def test_unknown_unary_operator(self):
        with self.assertRaises(CompileError):
            compile_ast(write(unary("~", c(1))))

    def test_statement_used_as_expression(self):
        loop = {"while": {"cond": c(0), "body": skip()}}
        with self.assertRaises(CompileError):
            compile_ast(write(binop("+", loop, c(1))))

    def test_missing_operand(self):
        with self.assertRaises(CompileError):
            compile_ast(write({"binop": "+", "left": c(1), "right": None}))

    def test_invalid_json_text(self):
        with self.assertRaises(ValueError):
            compile_text('{"write": ')


class CLITests(unittest.TestCase):
    def run_cmd(self, *args, input=""):
        return subprocess.run([sys.executable, *map(str, args)], input=input, text=True,
                              capture_output=True, cwd=ROOT)

    def test_compile_then_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "compiled.json"
            result = self.run_cmd("compiler.py", "program.json", "-o", out)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.run_cmd("stack_machine.py", out, input="5").stdout, "120\n")
            self.assertEqual(self.run_cmd("stack_machine.py", out, input="6").stdout, "720\n")

    def test_stdout_is_valid_machine_json(self):
        result = self.run_cmd("compiler.py", "program.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(parse_json_program(json.loads(result.stdout)))

    def test_asm_flag(self):
        result = self.run_cmd("compiler.py", "program.json", "--asm")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("JZ", result.stdout)

    def test_compile_error_exit_code(self):
        result = self.run_cmd("compiler.py", input='{"write": {"binop": "^", "left": 1, "right": 2}}')
        self.assertEqual(result.returncode, 1)
        self.assertIn("Compile error", result.stderr)


if __name__ == "__main__":
    unittest.main()
