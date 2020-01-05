from AST import AstNode
from context import Context
from dec_to_hex import dec_to_hex
from memory_stack import VirtualStackHelper
from opcodes import OpcodeList
from singleton import Singleton


class BuiltIns(metaclass=Singleton):
    def __init__(self, address_length):
        self.address_length = address_length
        self.__funcs = {
            'plus': self.__plus,
            'minus': self.__minus,
            'times': self.__times,
            'divide': self.__divide,

            'equal': self.__equal,
            'nonequal': self.__nonequal,
            'less': self.__less,
            'lesseq': self.__lesseq,
            'greater': self.__greater,
            'greatereq': self.__greatereq,

            'and': self.__and,
            'or': self.__or,
            'not': self.__not,

            'read': self.__read,

            # Special forms setq and return are listed as builtin functions because of similarity with default func
            'setq': self.__setq,
            'return': self.__return
        }

    def has(self, name: str):
        return name in self.__funcs

    def call(self, call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        self.__funcs[call_body.child_nodes[0].value](call_body, ctx, opcodes)

    def __read(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (1): | EoS | Value from input
        """
        assert len(body.child_nodes) == 2

        opcodes.add('PUSH', dec_to_hex(0x20, 2 * self.address_length))
        opcodes.add('MUL')

        opcodes.add('CALLDATALOAD')

    def __setq(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (1): | EoS | New Atom value
        OUTPUT (0): | EoS |
        """
        assert len(body.child_nodes) == 3

        atom_name = body.child_nodes[1].value
        address, is_new = ctx.get_atom_addr(atom_name)
        VirtualStackHelper().store_atom_value(opcodes, address)

    def __equal(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does value 1 equals value 2 (bool)
        """
        assert len(body.child_nodes) == 3

        opcodes.add('EQ')

    def __nonequal(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 differs from Value 2 (bool)
        """
        assert len(body.child_nodes) == 3

        opcodes.add('EQ')
        opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
        opcodes.add('EQ')

    def __not(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (1): | EoS | value (bool)
        OUTPUT (1): | EoS | !value (bool)
        """
        assert len(body.child_nodes) == 2

        opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
        opcodes.add('EQ')

    def __plus(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Sum of values
        """
        assert len(body.child_nodes) == 3

        opcodes.add('ADD')

    def __minus(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Value 1 - Value 2
        """

        assert len(body.child_nodes) == 3
        opcodes.add('SWAP1')
        opcodes.add('SUB')

    def __times(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Value 1 * Value 2
        """
        assert len(body.child_nodes) == 3

        opcodes.add('MUL')

    def __divide(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Value 1 // Value 2
        """
        assert len(body.child_nodes) == 3

        opcodes.add('SWAP1')
        opcodes.add('DIV')

    def __return(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (1): | EoS | Some value
        OUTPUT (0): | EoS |
        """
        assert len(body.child_nodes) == 2

        if ctx.is_prog:
            opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
            opcodes.add('MSTORE')
            opcodes.add('PUSH', dec_to_hex(32, 2 * self.address_length))
            opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
            opcodes.add('RETURN')
        else:
            VirtualStackHelper().load_back_address(opcodes)
            VirtualStackHelper().remove_frame(opcodes)
            opcodes.add('JUMP')


    def __less(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Is Value 1 lesser than Value 2
        """
        assert len(body.child_nodes) == 3

        opcodes.add('GT')

    def __lesseq(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        assert len(body.child_nodes) == 3

        opcodes.add('LT')
        opcodes.add('ISZERO')

    def __greater(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Is Value 1 greater than Value 2
        """
        assert len(body.child_nodes) == 3

        opcodes.add('LT')

    def __greatereq(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        assert len(body.child_nodes) == 3

        opcodes.add('GT')
        opcodes.add('ISZERO')

    def __or(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool)
        OUTPUT (1): | EoS | v1 OR v2 (bool)
        """
        assert len(body.child_nodes) == 3

        opcodes.add('OR')

    def __and(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool)
        OUTPUT (1): | EoS | v1 AND v2 (bool)
        """
        assert len(body.child_nodes) == 3

        opcodes.add('AND')