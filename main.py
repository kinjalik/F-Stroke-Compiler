import json
import sys

from AST import AST
from code_generator import generate_code
from tokenizer import TokenList

import logging

# add filemode="w" to overwrite
logging.basicConfig(level=logging.INFO, filename=sys.stdout)
main_logger = logging.getLogger('Main')
main_logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    main_logger.info('Starting program...')
    inputFile = open('input.fst', 'r')
    code = inputFile.read()
    main_logger.info('TokenЩizing the code')
    tokens = TokenList(code)
    main_logger.info('Building AST-Tree')
    tree = AST(tokens)
    main_logger.info('AST Built')
    main_logger.info('Writing AST to file...')
    jsonTreeOutput = open("ast.json", "w+")
    jsonTreeOutput.write(json.dumps(tree.to_dict(), indent=4))
    jsonTreeOutput.flush()
    jsonTreeOutput.close()
    main_logger.info('AST written to file.')
    print(generate_code(tree))
    main_logger.info('Shutdown...')