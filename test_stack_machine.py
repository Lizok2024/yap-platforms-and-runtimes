import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

from context import ExecutionContext
from stack_machine import StackMachine, parse_program, parse_json_program


ROOT = Path(__file__).resolve().parent


class MachineTests(unittest.TestCase):
    def test_website_json(self):
        text = (ROOT / "machine_example.json").read_text(encoding="utf-8")
        machine = StackMachine(parse_program(text), ExecutionContext([10]))
        output = io.StringIO()
        with redirect_stdout(output):
            machine.run()
        self.assertEqual(output.getvalue(), "7\n")
        self.assertEqual(machine.stack, [])
        self.assertEqual(machine.context.env.vars, {"x": 10})

    def test_json_jumps(self):
        raw = [{"CONST": 2}, {"ST": "n"}, {"LABEL": "loop"},
               {"LD": "n"}, {"CONST": 1}, {"BINOP": "-"}, {"ST": "n"},
               {"LD": "n"}, {"JNZ": "loop"}, {"CONST": 0}, {"JZ": "end"},
               {"JMP": "loop"}, {"LABEL": "end"}]
        machine = StackMachine(parse_program(json.dumps(raw)))
        machine.run(max_steps=100)
        self.assertEqual(machine.context.env.vars, {"n": 0})
        self.assertEqual(machine.stack, [])

    def test_invalid_json_instructions(self):
        for raw in [{"seq": {}}, ["LD"], ["BOGUS"], [42], [{}],
                    [{"BINOP": "!"}], [{"CONST": 1.5}], [{"CONST": True}], [{"CONST": "3"}], [{"LD": []}],
                    [{"READ": None}], [{"LD": "x", "ST": "y"}]]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                parse_program(json.dumps(raw))
        with self.assertRaises(ValueError):
            parse_program('["READ",')
        self.assertEqual(parse_program("[]"), [])

    def test_all_instructions(self):
        raw = ['READ', {'ST': 'n'}, {'CONST': 0}, {'ST': 's'}, {'LABEL': 'loop'}, {'LD': 'n'}, {'JZ': 'end'}, {'LD': 's'}, {'LD': 'n'}, {'BINOP': '+'}, {'ST': 's'}, {'LD': 'n'}, {'CONST': 1}, {'BINOP': '-'}, {'ST': 'n'}, {'JMP': 'loop'}, {'LABEL': 'end'}, {'LD': 's'}, 'WRITE', {'CONST': -1}, {'JNZ': 'done'}, {'CONST': 999}, 'WRITE', {'LABEL': 'done'}]
        machine = StackMachine(parse_json_program(raw), ExecutionContext([3]))
        output = io.StringIO()
        with redirect_stdout(output):
            machine.run(100)
        self.assertEqual(output.getvalue(), "6\n")
        self.assertEqual(machine.stack, [])
        self.assertEqual(machine.context.env.vars, {"n": 0, "s": 6})

    def test_conditional_jumps_pop_on_both_paths(self):
        for opcode in ["JZ", "JNZ"]:
            for value in [-3, 0, 1]:
                machine = StackMachine(parse_json_program(
                    [{"CONST": value}, {opcode: "target"}, {"CONST": 10}, {"LABEL": "target"}]))
                machine.run()
                taken = (value == 0) == (opcode == "JZ")
                self.assertEqual(machine.stack, [] if taken else [10])

    def test_operand_order(self):
        for op, expected in [("-", 5), ("/", 3), ("%", 1), ("<", 0)]:
            machine = StackMachine(parse_json_program([{"CONST": 7}, {"CONST": 2}, {"BINOP": op}]))
            machine.run()
            self.assertEqual(machine.stack, [expected])

    def test_invalid_labels(self):
        for raw in [[{"JMP": "absent"}], [{"CONST": 1}, {"JZ": "absent"}],
                    [{"LABEL": "a"}, {"LABEL": "a"}]]:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                StackMachine(parse_json_program(raw))

    def test_stack_underflow(self):
        for raw in [["WRITE"], [{"ST": "x"}], [{"BINOP": "+"}],
                    [{"CONST": 1}, {"BINOP": "-"}],
                    [{"JZ": "a"}, {"LABEL": "a"}], [{"JNZ": "a"}, {"LABEL": "a"}]]:
            with self.subTest(raw=raw), self.assertRaisesRegex(RuntimeError, "underflow"):
                StackMachine(parse_json_program(raw)).run()

    def test_runtime_errors(self):
        for raw, error in [([{"LD": "missing"}], NameError), (["READ"], EOFError),
                           ([{"CONST": 1}, {"CONST": 0}, {"BINOP": "/"}], ZeroDivisionError)]:
            with self.subTest(raw=raw), self.assertRaises(error):
                StackMachine(parse_json_program(raw)).run()

    def test_infinite_loop_limit(self):
        machine = StackMachine(parse_json_program([{"LABEL": "loop"}, {"JMP": "loop"}]))
        with self.assertRaisesRegex(RuntimeError, "limit"):
            machine.run(max_steps=20)
        self.assertEqual(machine.stack, [])

    def test_binary_operations(self):
        for op, expected in [("+", -4), ("-", -10), ("*", -21), ("/", -3),
                             ("%", 2), ("==", 0), ("!=", 1), ("<", 1),
                             ("<=", 1), (">", 0), (">=", 0), ("&&", 1), ("||", 1)]:
            with self.subTest(op=op):
                machine = StackMachine(parse_json_program([{"CONST": -7}, {"CONST": 3}, {"BINOP": op}]))
                machine.run()
                self.assertEqual(machine.stack, [expected])

    def test_empty_program(self):
        machine = StackMachine(parse_program("[]"))
        machine.run()
        self.assertEqual(machine.stack, [])



class CLITests(unittest.TestCase):
    def test_website_json_file(self):
        self.assertEqual(self.command("stack_machine.py", "machine_example.json",
                                      input="10"), "7\n")

    def command(self, *args, input=""):
        return subprocess.run([sys.executable, *map(str, args)], input=input,
                              text=True, capture_output=True, cwd=ROOT, check=True).stdout

    def test_factorial_file(self):
        for value, expected in [(0, 1), (1, 1), (5, 120), (6, 720)]:
            with self.subTest(value=value):
                self.assertEqual(self.command("stack_machine.py", "machine_factorial.json",
                                              input=str(value)), f"{expected}\n")


if __name__ == "__main__":
    unittest.main()
