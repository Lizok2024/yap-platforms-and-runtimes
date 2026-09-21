from environment import Environment


class ExecutionContext:
    def __init__(self, input_tokens=None):
        self.env = Environment()
        self.input_tokens = list(input_tokens or [])
        self.pos = 0

    def read_int(self) -> int:
        if self.pos >= len(self.input_tokens):
            raise EOFError("No input available for read operation")
        token = self.input_tokens[self.pos]
        self.pos += 1
        return int(token)

    def write(self, value):
        print(value)
