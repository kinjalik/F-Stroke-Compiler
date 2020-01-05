from AST import AstNode, AstNodeType
from code_generator import Context, OpcodeList, ByteCodeGenerator, dec_to_hex, VirtualStackHelper, FRAME_SERVICE_ATOMS


class Declared:
    addr_by_name: dict = {}

    @staticmethod
    def call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.List
        assert call_body.child_nodes[0].type == AstNodeType.Literal or call_body.child_nodes[0].type == AstNodeType.Atom

        # Prepare arguments
        for i in range(1, len(call_body.child_nodes)):
            ByteCodeGenerator().process_call(call_body.child_nodes[i], ctx)

        # Prepare back address, part 1
        opcodes.add('PUSH')
        back_address = len(opcodes.list) - 1

        # Jump into the function
        opcodes.add('PUSH', dec_to_hex(Declared.addr_by_name[call_body.child_nodes[0].value]))
        opcodes.add('JUMP')

        # Prepare back address, part 2
        opcodes.add('JUMPDEST')
        opcodes.list[back_address].extra_value = dec_to_hex(opcodes.list[-1].id)

    @staticmethod
    def declare(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.List
        assert call_body.child_nodes[0].type == AstNodeType.Literal or call_body.child_nodes[0].type == AstNodeType.Atom
        assert call_body.child_nodes[0].value == 'func'
        """
        INPUT:  | EoS | Arg1 | ... | ArgN | Back address
        OUTPUT: | EoS |
        """
        # Set entry point
        opcodes.add('JUMPDEST')
        Declared.addr_by_name[call_body.child_nodes[1].value] = opcodes.list[-1].id

        # Make new stack frame
        # Back address gone
        VirtualStackHelper.add_frame(opcodes)

        # Set atom counter, part 1
        opcodes.add('PUSH')
        func_atom_counter = len(opcodes.list) - 1
        VirtualStackHelper.load_cur_atom_counter_addr(opcodes)
        opcodes.add('MSTORE')

        # Declare arguments in context
        # Args gone
        for arg_name in reversed(call_body.child_nodes[2].child_nodes):
            assert arg_name.type == AstNodeType.Atom
            address, is_new = ctx.get_atom_addr(arg_name.value)
            VirtualStackHelper.store_atom_value(opcodes, address)

        # Generate body
        ByteCodeGenerator(None).process_call(call_body.child_nodes[3], ctx)

        # Set atom counter, part 2
        opcodes.list[func_atom_counter].extra_value = dec_to_hex(ctx.counter - FRAME_SERVICE_ATOMS)

        # Remove frame and leave function
        VirtualStackHelper.load_back_address(opcodes)
        VirtualStackHelper.remove_frame(opcodes)
        opcodes.add('JUMP')