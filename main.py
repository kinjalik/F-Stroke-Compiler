from AST import AST
from tokenizer import TokenList

import logging

# add filemode="w" to overwrite
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('Main')
logger.setLevel(logging.DEBUG)

if __name__ == '__main__':
    logger.info('Starting program...')
    inputFile = open('input.fst', 'r')
    code = inputFile.read()
    logger.info('Tokenizing the code')
    tokens = TokenList(code)
    logger.info('Building AST-Tree')
    tree = AST(tokens)
    logger.info('AST-Tree Built')
    print(tree)
    logger.info('Shutdown...')
