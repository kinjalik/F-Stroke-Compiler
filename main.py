import sys

from AST import AST
from code_generator import generate_code
from tokenizer import TokenList

if __name__ == '__main__':
    code = open('input.fst').read()
    # code = sys.stdin.read()
    tokens = TokenList(code)
    tree = AST(tokens)
    print(generate_code(tree))