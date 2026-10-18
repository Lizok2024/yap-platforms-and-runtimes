import sys

from interpreter import Interpreter


def main():
    data = sys.stdin.read()
    if data.strip():
        Interpreter().interpret_text(data)


if __name__ == "__main__":
    main()
