from enum import Enum
from typing import Any, List

from tokenizer import TokenList, Terminal

tokenList: TokenList


class AstNodeType(Enum):
    Program = 0
    List = 1
    Element = 2
    Atom = 3
    Literal = 4
    Identifier = 5
    Integer = 6


class AstNode:
    type: AstNodeType
    value: Any
    child_nodes: List = list()

    def __init__(self, node_type: AstNodeType, value: Any):
        self.type = node_type
        self.value = value
        self.child_nodes = list()

    def add_child(self, child_node):
        self.child_nodes.append(child_node)

    @staticmethod
    def build_program():
        global tokenList
        node = AstNode(AstNodeType.Program, None)
        while tokenList.get_current_token().type != Terminal.EOF:
            if tokenList.get_current_token().type == Terminal.SPACE:
                tokenList.inc()
                continue
            node.add_child(AstNode.build_element())
        return node

    @staticmethod
    def build_element():
        global tokenList
        if tokenList.get_current_token().type == Terminal.Letter:
            return AstNode.build_atom()
        elif tokenList.get_current_token().type == Terminal.Digit:
            return AstNode.build_literal()
        elif tokenList.get_current_token().type == Terminal.LP:
            return AstNode.build_list()

    @staticmethod
    def build_list():
        global tokenList
        node = AstNode(AstNodeType.List, None)

        tokenList.inc()
        while tokenList.get_current_token().type != Terminal.RP:
            if tokenList.get_current_token().type == Terminal.SPACE:
                tokenList.inc()
                continue
            node.add_child(AstNode.build_element())
        tokenList.inc()

        return node

    @staticmethod
    def build_atom():
        global tokenList
        node = AstNode(AstNodeType.Atom, None)

        value: str = tokenList.get_current_token().value

        tokenList.inc()
        while tokenList.get_current_token().type == Terminal.Letter or \
                tokenList.get_current_token().type == Terminal.Digit:
            value += tokenList.get_current_token().value
            tokenList.inc()

        node.value = value.lower()
        return node

    @staticmethod
    def build_literal():
        global tokenList
        node = AstNode(AstNodeType.Literal, None)
        value = tokenList.get_current_token().value

        tokenList.inc()
        while tokenList.get_current_token().type == Terminal.Digit:
            value += tokenList.get_current_token().value
            tokenList.inc()

        node.value = int(value)
        return node


class AST:
    root: AstNode

    def __init__(self, token_list: TokenList):
        global tokenList
        tokenList = token_list
        tokenList.set_current_token_index(0)
        self.root = AstNode.build_program()
