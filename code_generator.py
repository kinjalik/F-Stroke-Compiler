from context import Context
from dec_to_hex import dec_to_hex
from AST import AST, AstNode, AstNodeType
from fst_functions.builtin import BuiltIns
from fst_functions.declared import Declared
from memory_stack import VirtualStackHelper
from opcodes import OpcodeList
from singleton import Singleton


class Generator(metaclass=Singleton):
    opcodes: OpcodeList
    address_length: int
    frame_service_atoms: int

    def __init__(self, ast: AST, address_length=2, frame_service_atoms=3):
        self.address_length = address_length
        self.frame_service_atoms = frame_service_atoms

        assert 32 >= address_length >= 1
        assert frame_service_atoms >= 2

        self.opcodes: OpcodeList = OpcodeList(address_length)
        self.__ast = ast

        # Init Virtual stack and function Singletons
        VirtualStackHelper(address_length, frame_service_atoms).init_stack(self.opcodes)
        SpecialForms(address_length)
        BuiltIns(self.address_length)
        Declared(address_length, frame_service_atoms)

    def run(self):
        # Set jump to main program body
        self.opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
        jump_to_prog_start_i = len(self.opcodes.list) - 1
        self.opcodes.add('JUMP')

        for el in self.__ast.root.child_nodes:
            context = Context(self.frame_service_atoms)

            if el.child_nodes[0].value == 'prog':
                context.is_prog = True
                # Jump from header to prog body
                self.opcodes.add('JUMPDEST')
                self.opcodes.list[jump_to_prog_start_i].extra_value = dec_to_hex(self.opcodes.list[-1].id,
                                                                                 2 * self.address_length)

                self.opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
                prog_atom_count = len(self.opcodes.list) - 1
                VirtualStackHelper().load_cur_atom_counter_addr(self.opcodes)
                self.opcodes.add('MSTORE')

                self.process_code_block(el.child_nodes[1], context, self.opcodes)

                self.opcodes.list[prog_atom_count].extra_value = dec_to_hex(context.counter - self.frame_service_atoms,
                                                                            2 * self.address_length)

            else:
                self.declare_function(el, context, self.opcodes)
        return self

    def __str__(self):
        byte_code = self.opcodes.get_str()
        return byte_code

    def process_code_block(self, prog_body: AstNode, ctx: Context, opcodes: OpcodeList):
        # assert prog_body.type == AstNodeType.List
        for call in prog_body.child_nodes:
            self.process_call(call, ctx, opcodes)

    def process_call(self, call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        # Processing syntax features: literals, atoms
        if call_body.type == AstNodeType.Literal:
            return self.process_literal(call_body, opcodes)

        if call_body.type == AstNodeType.Atom:
            return self.process_atom(call_body, ctx, opcodes)

        # Processing block of code
        if call_body.type == AstNodeType.List and call_body.child_nodes[0].type == AstNodeType.List:
            return self.process_code_block(call_body, ctx, opcodes)

        # Processing pre-built functions
        name = call_body.child_nodes[0].value

        # If we have a special form incoming, we delegate full processing to it
        if SpecialForms().has(name):
            return SpecialForms().call(call_body, ctx, opcodes, self)

        # Else we prepare an arguments and calls a function
        for i in range(1, len(call_body.child_nodes)):
            self.process_call(call_body.child_nodes[i], ctx, opcodes)

        if BuiltIns().has(name):
            return BuiltIns().call(call_body, ctx, opcodes)

        if Declared().has(name):
            return Declared().call(call_body, ctx, opcodes)

        return 0

    def process_literal(self, call_body: AstNode, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.Literal
        value = dec_to_hex(call_body.value, 2 * self.address_length)
        opcodes.add('PUSH', value)

    def process_atom(self, call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.Atom
        atom_name = call_body.value
        atom_address, is_new = ctx.get_atom_addr(atom_name)
        VirtualStackHelper().load_atom_value(opcodes, atom_address)

    def declare_function(self, call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.List
        assert call_body.child_nodes[0].type == AstNodeType.Literal or call_body.child_nodes[0].type == AstNodeType.Atom
        assert call_body.child_nodes[0].value == 'func'
        """
        INPUT:  | EoS | Arg1 | ... | ArgN | Back address
        OUTPUT: | EoS |
        """
        # Set entry point
        opcodes.add('JUMPDEST')
        Declared().add(call_body.child_nodes[1].value, opcodes.list[-1].id)

        # Make new stack frame
        # Back address gone
        VirtualStackHelper().add_frame(opcodes)

        # Set atom counter, part 1
        opcodes.add('PUSH')
        func_atom_counter = len(opcodes.list) - 1
        VirtualStackHelper().load_cur_atom_counter_addr(opcodes)
        opcodes.add('MSTORE')

        # Declare arguments in context
        # Args gone
        for arg_name in reversed(call_body.child_nodes[2].child_nodes):
            assert arg_name.type == AstNodeType.Atom
            address, is_new = ctx.get_atom_addr(arg_name.value)
            VirtualStackHelper().store_atom_value(opcodes, address)

        # Generate body
        self.process_call(call_body.child_nodes[3], ctx, opcodes)

        # Set atom counter, part 2
        opcodes.list[func_atom_counter].extra_value = dec_to_hex(ctx.counter - self.frame_service_atoms,
                                                                 2 * self.address_length)

        # Remove frame and leave function
        VirtualStackHelper().load_back_address(opcodes)
        VirtualStackHelper().remove_frame(opcodes)
        opcodes.add('JUMP')


class SpecialForms(metaclass=Singleton):

    def __init__(self, address_length: int):
        self.__funcs = {
            'cond': SpecialForms.__cond,
            'while': SpecialForms.__while,
            'break': SpecialForms.__break
        }
        self.while_count = 0
        self.current_while = 0
        self.address_length = address_length

    def has(self, name: str):
        return name in self.__funcs

    def call(self, body: AstNode, ctx: Context, opcodes: OpcodeList, generator: Generator):
        self.__funcs[body.child_nodes[0].value](self, body, ctx, opcodes, generator)

    def __cond(self, body: AstNode, ctx: Context, opcodes: OpcodeList, generator: Generator):
        """
        INPUT  (0): | EoS |
        OUTPUT (0): | EoS |
        """
        assert len(body.child_nodes) == 3 or len(body.child_nodes) == 4

        # Conditions check
        generator.process_call(body.child_nodes[1], ctx, opcodes)
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
        opcodes.list[jump_from_check_to_true].extra_value = dec_to_hex(block_id, 2 * self.address_length)
        generator.process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('PUSH', )
        jump_from_true_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # FALSE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_false].extra_value = dec_to_hex(block_id, 2 * self.address_length)
        if len(body.child_nodes) == 4:
            generator.process_call(body.child_nodes[3], ctx, opcodes)
        opcodes.add('PUSH')
        jump_from_false_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # END
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_true_to_end].extra_value = dec_to_hex(block_id, 2 * self.address_length)
        opcodes.list[jump_from_false_to_end].extra_value = dec_to_hex(block_id, 2 * self.address_length)

    def __break(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        assert len(body.child_nodes) == 1
        opcodes.add('PUSH', dec_to_hex(0, 2 * self.address_length))
        opcodes.add('JUMP', dec_to_hex(self.current_while, 2 * self.address_length))
        pass

    def __while(self, body: AstNode, ctx: Context, opcodes: OpcodeList, generator: Generator):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        assert len(body.child_nodes) == 3
        prev_while = self.current_while
        self.current_while = self.while_count
        self.while_count += 1
        opcodes.add('JUMPDEST', dec_to_hex(self.current_while, 2 * self.address_length))
        jumpdest_to_condition_check_id = dec_to_hex(opcodes.list[-1].id, 2 * self.address_length)
        generator.process_call(body.child_nodes[1], ctx, opcodes)
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
        opcodes.list[jump_to_while_body].extra_value = dec_to_hex(opcodes.list[-1].id, 2 * self.address_length)
        generator.process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('PUSH', jumpdest_to_condition_check_id)
        opcodes.add('JUMP')
        # while end
        opcodes.add('JUMPDEST')
        opcodes.list[jump_to_while_end].extra_value = dec_to_hex(opcodes.list[-1].id, 2 * self.address_length)
        for i in range(len(opcodes.list)):
            if opcodes.list[i].name == 'JUMP' and opcodes.list[i].extra_value == dec_to_hex(self.current_while,
                                                                                            2 * self.address_length):
                opcodes.list[i - 1].extra_value = dec_to_hex(opcodes.list[-1].id, 2 * self.address_length)
                opcodes.list[i].extra_value = None
        BuiltIns.current_while = prev_while
