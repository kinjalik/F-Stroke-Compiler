import json
import sys

from AST import AST
from code_generator import generate_code
from tokenizer import TokenList

import logging

# add filemode="w" to overwrite
logging.basicConfig(level=logging.INFO, filename=sys.stdout)
logger = logging.getLogger('Main')
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    logger.info('Starting program...')
    inputFile = open('input.fst', 'r')
    code = inputFile.read()
    logger.info('TokenЩizing the code')
    tokens = TokenList(code)
    logger.info('Building AST-Tree')
    tree = AST(tokens)
    logger.info('AST Built')
    logger.info('Writing AST to file...')
    jsonTreeOutput = open("ast.json", "w+")
    jsonTreeOutput.write(json.dumps(tree.to_dict(), indent=4))
    jsonTreeOutput.flush()
    jsonTreeOutput.close()
    logger.info('AST written to file.')
    print(generate_code(tree))
    logger.info('Shutdown...')