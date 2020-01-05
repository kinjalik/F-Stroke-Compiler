from AST import AstNode, AstNodeType
from context import Context
from utils import dec_to_hex
from opcodes import OpcodeList
from singleton import Singleton


class Declared(metaclass=Singleton):
    def __init__(self, address_length, frame_service_atoms):
        self.address_length = address_length
        self.frame_service_atoms = frame_service_atoms
        self.__funcs = {}

    def has(self, name: str):
        return name in self.__funcs

    def add(self, name: str, address: int):
        self.__funcs[name] = address

    def call(self, call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.List
        assert call_body.child_nodes[0].type == AstNodeType.Literal or call_body.child_nodes[0].type == AstNodeType.Atom

        # Prepare back address, part 1
        opcodes.add('PUSH')
        back_address = len(opcodes.list) - 1

        # Jump into the function
        opcodes.add('PUSH', dec_to_hex(self.__funcs[call_body.child_nodes[0].value], 2 * self.address_length))
        opcodes.add('JUMP')

        # Prepare back address, part 2
        opcodes.add('JUMPDEST')
        opcodes.list[back_address].extra_value = dec_to_hex(opcodes.list[-1].id, 2 * self.address_length)