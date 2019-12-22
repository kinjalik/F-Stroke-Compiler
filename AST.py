from enum import Enum
from typing import Generic, List, Any
from tokenizer import TokenList, Terminal as TokenType

import logging

tokenList: TokenList
logging.basicConfig(level=logging.DEBUG)

logger = logging.getLogger('AST_Builder')
logger.setLevel(logging.DEBUG)


class Type(Enum):
    Program = 0
    List = 1
    Element = 2
    Atom = 3
    Literal = 4
    Identifier = 5
    Integer = 6


class AstNode:
    type: Type
    value: Any
    child_nodes: List = list()

    def __init__(self, type: Type, value: Any):
        self.type = type
        self.value = value
        self.child_nodes = list()

    def add_child(self, child_node):
        self.child_nodes.append(child_node)

    def to_dict(self):
        res = {
            'type': self.type.name,
        }

        child_nodes = []
        if len(self.child_nodes) != 0:
            for x in self.child_nodes:
                child_nodes.append(x.to_dict())
            res['child_nodes'] = child_nodes
        if self.value is not None:
            res['value'] = self.value
        return res

    @staticmethod
    def process_program():
        global tokenList
        logger.debug('Building node: Program')
        node = AstNode(Type.Program, None)
        token = tokenList.get_current_token()
        while token.type != TokenType.EOF:
            if token.type == TokenType.SPACE:
                tokenList.inc()
            node.add_child(AstNode.process_element())
            token = tokenList.get_current_token()
        return node

    @staticmethod
    def process_element():
        global tokenList
        logger.debug('Building node: Element')
        node = AstNode(Type.Element, None)
        token = tokenList.get_current_token()
        if token.type == TokenType.Letter:
            node.add_child(AstNode.process_atom())
        elif token.type == TokenType.Digit:
            node.add_child(AstNode.process_literal())
        elif token.type == TokenType.LP:
            node.add_child(AstNode.process_list())
        return node

    @staticmethod
    def process_list():
        global tokenList
        logger.debug('Building node: List')
        node = AstNode(Type.List, None)

        token = tokenList.get_current_token()
        assert token.type == TokenType.LP
        tokenList.inc()
        token = tokenList.get_current_token()
        while token.type == TokenType.SPACE and tokenList.get_next_token().type != TokenType.RP:
            tokenList.inc()
            node.add_child(AstNode.process_element())
            token = tokenList.get_current_token()
        assert token.type == TokenType.SPACE and tokenList.get_next_token().type == TokenType.RP
        tokenList.inc()
        tokenList.inc()
        return node

    # @staticmethod
    # def process_atom():
    #     global tokenList
    #     logger.debug('Building node: Atom')
    #     node = AstNode(Type.Atom, None)
    #     node.add_child(AstNode.process_identifier())
    #     return node

    @staticmethod
    def process_atom():
        global tokenList
        logger.debug('Building node: Atom')
        node = AstNode(Type.Atom, None)

        token = tokenList.get_current_token()
        assert token.type == TokenType.Letter
        value = token.value

        tokenList.inc()
        token = tokenList.get_current_token()
        while token.type == TokenType.Letter or token.type == TokenType.Digit:
            value += token.value
            tokenList.inc()
            token = tokenList.get_current_token()

        node.value = value
        return node

    @staticmethod
    def process_literal():
        global tokenList
        logger.debug('Building node: Literal')
        node = AstNode(Type.Literal, None)

        token = tokenList.get_current_token()
        assert token.type == TokenType.Digit
        value = token.value

        tokenList.inc()
        token = tokenList.get_current_token()
        while token.type == TokenType.Digit:
            value += token.value
            tokenList.inc()
            token = tokenList.get_current_token()

        node.value = int(value)
        return node


class AST:
    root: AstNode

    def __init__(self, token_list: TokenList):
        logger.info('Starting build of AST')
        global tokenList
        tokenList = token_list
        tokenList.set_current_token_index(0)
        self.root = AstNode.process_program()

    def to_dict(self):
        return {
            'root': self.root.to_dict()
        }