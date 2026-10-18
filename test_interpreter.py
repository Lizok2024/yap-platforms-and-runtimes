import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from interpreter import Interpreter, main


class InterpreterTests(unittest.TestCase):
    def test_runs_ast_program(self):
        program = {
            "input": "5",
            "write": {
                "binop": {
                    "op": "+",
                    "left": {"const": 2},
                    "right": {"const": 3},
                }
            },
        }
        output = io.StringIO()
        with redirect_stdout(output):
            Interpreter().interpret(program)
        self.assertEqual(output.getvalue().strip(), "5")

    def test_sum_arrays(self):
        self.assertEqual(Interpreter.sum_arrays([[1, 2, 3], [4, 5], [], [6, [7, 8]]]), 36)

    def test_sum_flat_array(self):
        self.assertEqual(Interpreter.sum_arrays([1, -2, 3]), 2)

    def test_sum_empty_array(self):
        self.assertEqual(Interpreter.sum_arrays([]), 0)

    def test_sum_decimal_numbers(self):
        self.assertEqual(Interpreter.sum_arrays([[1.5, 2], [3.25]]), 6.75)

    def test_sum_rejects_strings(self):
        with self.assertRaises(TypeError):
            Interpreter.sum_arrays([[1, "2"]])

    def test_sum_rejects_boolean(self):
        with self.assertRaises(TypeError):
            Interpreter.sum_arrays([True, 1])

    def test_cli_sum_arrays_file(self):
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["--sum-arrays", "sum_arrays.json"])
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "36")

    def test_cli_sum_arrays_stdin(self):
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO("[[1, 2], [3]]")):
            with redirect_stdout(output):
                result = main(["--sum-arrays"])
        self.assertEqual(result, 0)
        self.assertEqual(output.getvalue().strip(), "6")


if __name__ == "__main__":
    unittest.main()
