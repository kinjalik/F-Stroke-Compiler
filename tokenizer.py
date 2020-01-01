from enum import Enum
from typing import List


class Terminal(Enum):
    UNKNOWN = -1
    EOF = 1
    SPACE = 2
    LP = 3
    RP = 4
    Letter = 5
    Digit = 6


class Token:
    type: Terminal
    value: str

    def __init__(self, char: str):
        self.value = char
        if char == ' ':
            self.type = Terminal.SPACE
        elif char == '(':
            self.type = Terminal.LP
        elif char == ')':
            self.type = Terminal.RP
        elif char in '1234567890':
            self.type = Terminal.Digit
        elif char in 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM':
            self.type = Terminal.Letter
        elif char == chr(0):
            self.type = Terminal.EOF
        else:
            self.type = Terminal.UNKNOWN

    @staticmethod
    def get_eof():
        return Token(chr(0))


class TokenList:
    tokens: List[Token]
    length: int
    currentTokenIndex: int

    def __init__(self, rawCode: str):
        self.tokens = [Token(x) for x in preprocess_code(rawCode)]
        self.tokens.append(Token.get_eof())
        self.length = len(self.tokens)
        self.currentTokenIndex = 0

    def __len__(self):
        return self.length

    def set_current_token_index(self, val: int) -> None:
        self.currentTokenIndex = val

    def get_current_token_index(self) -> int:
        return self.currentTokenIndex

    def get_current_token(self) -> Token:
        return self.tokens[self.currentTokenIndex]

    def get_next_token(self) -> Token:
        return self.tokens[self.currentTokenIndex + 1]

    def inc(self):
        self.currentTokenIndex += 1


def preprocess_code(formatted_code: str):
    formatted_code = formatted_code.replace('\n', ' ')
    formatted_code = formatted_code.replace('\t', ' ')
    while '  ' in formatted_code:
        formatted_code = formatted_code.replace('  ', ' ')
    while formatted_code[-1] == ' ':
        formatted_code = formatted_code[:-1]

    return formatted_code


def get_tokens_array(rawCode: str):
    return [Token(x) for x in preprocess_code(rawCode)]
