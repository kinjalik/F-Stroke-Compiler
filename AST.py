import sys
import time
from enum import Enum
from typing import Generic, List, Any
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

    def __init__(self, type: AstNodeType, value: Any):
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
        node = AstNode(AstNodeType.Program, None)
        token = tokenList.get_current_token()
        while token.type != Terminal.EOF:
            while tokenList.get_current_token().type == Terminal.SPACE:
                tokenList.inc()
            node.add_child(AstNode.process_element())
            token = tokenList.get_current_token()
        return node

    @staticmethod
    def process_element():
        global tokenList
        node = AstNode(AstNodeType.Element, None)
        if tokenList.get_current_token().type == Terminal.Letter:
            return AstNode.process_atom()
        elif tokenList.get_current_token().type == Terminal.Digit:
            return AstNode.process_literal()
        elif tokenList.get_current_token().type == Terminal.LP:
            return AstNode.process_list()
        return node

    @staticmethod
    def process_list():
        global tokenList
        node = AstNode(AstNodeType.List, None)

        assert tokenList.get_current_token().type == Terminal.LP
        tokenList.inc()
        while tokenList.get_current_token().type != Terminal.RP:
            if tokenList.get_current_token().type == Terminal.RP:
                break
            if tokenList.get_current_token().type == Terminal.SPACE:
                tokenList.inc()
                continue
            node.add_child(AstNode.process_element())
        assert tokenList.get_current_token().type == Terminal.RP
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
        node = AstNode(AstNodeType.Atom, None)

        assert tokenList.get_current_token().type == Terminal.Letter

        value = tokenList.get_current_token().value

        tokenList.inc()
        while tokenList.get_current_token().type == Terminal.Letter or tokenList.get_current_token().type == Terminal.Digit:
            value += tokenList.get_current_token().value
            tokenList.inc()

        node.value = value
        return node

    @staticmethod
    def process_literal():
        global tokenList
        node = AstNode(AstNodeType.Literal, None)

        assert tokenList.get_current_token().type == Terminal.Digit
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
        self.root = AstNode.process_program()

    def to_dict(self):
        return {
            'root': self.root.to_dict()
        }