from AST import AstNode
from code_generator import Context, OpcodeList, ByteCodeGenerator, dec_to_hex, VirtualStackHelper


class BuiltIns:
    @staticmethod
    def read(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (1): | EoS | Value from input
        """
        assert len(body.child_nodes) == 2

        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)

        opcodes.add('PUSH', dec_to_hex(0x20))
        opcodes.add('MUL')

        opcodes.add('CALLDATALOAD')

    @staticmethod
    def cond(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (0): | EoS |
        """
        assert len(body.child_nodes) == 3 or len(body.child_nodes) == 4

        # Conditions check
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        # JUMP TO TRUE
        opcodes.add('PUSH')
        jump_from_check_to_true = len(opcodes.list) - 1
        opcodes.add('JUMPI')
        # JUMP TO ELSE
        opcodes.add('PUSH')
        jump_from_check_to_false = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # TRUE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_true].extra_value = dec_to_hex(block_id)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        opcodes.add('PUSH', )
        jump_from_true_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # FALSE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_false].extra_value = dec_to_hex(block_id)
        if len(body.child_nodes) == 4:
            ByteCodeGenerator().process_call(body.child_nodes[3], ctx)
        opcodes.add('PUSH')
        jump_from_false_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # END
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_true_to_end].extra_value = dec_to_hex(block_id)
        opcodes.list[jump_from_false_to_end].extra_value = dec_to_hex(block_id)

    @staticmethod
    def setq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        """
        INPUT  (1): | EoS | New Atom value
        OUTPUT (0): | EoS |
        """

        assert len(body.child_nodes) == 3

        atom_name = body.child_nodes[1].value
        address, is_new = ctx.get_atom_addr(atom_name)
        VirtualStackHelper.store_atom_value(opcodes, address)

    @staticmethod
    def equal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Does value 1 equals value 2 (bool)
        """

        assert len(body.child_nodes) == 3

        opcodes.add('EQ')

    @staticmethod
    def nonequal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 differs from Value 2 (bool)
        """
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)

        assert len(body.child_nodes) == 3

        opcodes.add('EQ')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('EQ')

    @staticmethod
    def nnot(body: AstNode, ctx: Context, opcodes: OpcodeList):
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        """
        INPUT  (1): | EoS | value (bool)
        OUTPUT (1): | EoS | !value (bool)
        """
        assert len(body.child_nodes) == 2
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('EQ')

    @staticmethod
    def plus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Sum of values
        """
        assert len(body.child_nodes) == 3
        opcodes.add('ADD')

    @staticmethod
    def minus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Value 1 - Value 2
        """
        assert len(body.child_nodes) == 3
        opcodes.add('SWAP1')
        opcodes.add('SUB')

    @staticmethod
    def times(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Value 1 * Value 2
        """
        assert len(body.child_nodes) == 3
        opcodes.add('MUL')

    @staticmethod
    def divide(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Value 1 // Value 2
        """
        assert len(body.child_nodes) == 3
        opcodes.add('SWAP1')
        opcodes.add('DIV')

    @staticmethod
    def rreturn(body: AstNode, ctx: Context, opcodes: OpcodeList):
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        """
        INPUT  (1): | EoS | Some value 
        OUTPUT (0): | EoS | 
        """
        assert len(body.child_nodes) == 2
        if ctx.is_prog:
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MSTORE')
            opcodes.add('PUSH', dec_to_hex(32))
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('RETURN')
        else:
            VirtualStackHelper.load_back_address(opcodes)
            VirtualStackHelper.remove_frame(opcodes)
            opcodes.add('JUMP')

    while_count = 0
    current_while = 0

    @staticmethod
    def bbreak(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        assert len(body.child_nodes) == 1
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('JUMP', dec_to_hex(BuiltIns.current_while))
        pass

    @staticmethod
    def wwhile(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        assert len(body.child_nodes) == 3
        prev_while = BuiltIns.current_while
        BuiltIns.current_while = BuiltIns.while_count
        BuiltIns.while_count += 1
        opcodes.add('JUMPDEST', dec_to_hex(BuiltIns.current_while))
        jumpdest_to_condition_check_id = dec_to_hex(opcodes.list[-1].id)
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        # if true: jump to while body
        opcodes.add('PUSH')
        jump_to_while_body = len(opcodes.list) - 1
        opcodes.add('JUMPI')
        # else: jump to while end
        opcodes.add('PUSH')
        jump_to_while_end = len(opcodes.list) - 1
        opcodes.add('JUMP')

        # while body
        opcodes.add('JUMPDEST')
        opcodes.list[jump_to_while_body].extra_value = dec_to_hex(opcodes.list[-1].id)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        opcodes.add('PUSH', jumpdest_to_condition_check_id)
        opcodes.add('JUMP')
        # while end
        opcodes.add('JUMPDEST')
        opcodes.list[jump_to_while_end].extra_value = dec_to_hex(opcodes.list[-1].id)
        for i in range(len(opcodes.list)):
            if opcodes.list[i].name == 'JUMP' and opcodes.list[i].extra_value == dec_to_hex(BuiltIns.current_while):
                opcodes.list[i - 1].extra_value = dec_to_hex(opcodes.list[-1].id)
                opcodes.list[i].extra_value = None
        BuiltIns.current_while = prev_while

    @staticmethod
    def less(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Is Value 1 lesser than Value 2
        """
        assert len(body.child_nodes) == 3
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        # | n | b | EOS |
        # b < n
        opcodes.add('GT')

    @staticmethod
    def lesseq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        assert len(body.child_nodes) == 3
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        opcodes.add('EQ')
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        # | n | b | EOS |
        # b < n
        opcodes.add('GT')
        opcodes.add('OR')

    '''
    ( greater A B )
    Stack: | B | A | EOS |
    B < A
    '''

    @staticmethod
    def greater(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Is Value 1 greater than Value 2
        """
        assert len(body.child_nodes) == 3
        opcodes.add('LT')

    @staticmethod
    def greatereq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        assert len(body.child_nodes) == 3
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        opcodes.add('EQ')
        ByteCodeGenerator().process_call(body.child_nodes[1], ctx)
        ByteCodeGenerator().process_call(body.child_nodes[2], ctx)
        # | n | b | EOS |
        # b < n
        opcodes.add('LT')
        opcodes.add('OR')

    @staticmethod
    def oor(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool) 
        OUTPUT (1): | EoS | v1 OR v2 (bool)
        """
        assert len(body.child_nodes) == 3
        opcodes.add('OR')

    @staticmethod
    def aand(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            ByteCodeGenerator().process_call(body.child_nodes[i], ctx)
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool) 
        OUTPUT (1): | EoS | v1 AND v2 (bool)
        """
        assert len(body.child_nodes) == 3
        opcodes.add('AND')