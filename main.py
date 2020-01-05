import sys
import argparse
import logging

from AST import AST
from code_generator import Generator
from tokenizer import TokenList


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='F-Stroke Language Compiler')
    parser.add_argument('input', type=str, help='File to input with F-Stroke code', default='input.fst')
    parser.add_argument('-o', type=str, help='File to output with Ethereum Byte Code', default='output.ebc')
    parser.add_argument('--hex-size', type=int, help='Size of hex numbers in bytes (max 32)', default=32)
    args = parser.parse_args()

    code = open(args.input).read()
    tokens = TokenList(code)
    tree = AST(tokens)
    output = open(args.o, 'w+')
    output.write(str(Generator(tree, args.hex_size).run()))
    output.flush()
    output.close()
