import sys

from AST import AST
from code_generator import Generator
from tokenizer import TokenList

if __name__ == '__main__':
    code = open('input.fst').read()
    # code = sys.stdin.read()
    tokens = TokenList(code)
    tree = AST(tokens)
    print(Generator(tree).get_byte_code())