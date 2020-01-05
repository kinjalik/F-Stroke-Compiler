from context import Context
from dec_to_hex import dec_to_hex
from AST import AST, AstNode, AstNodeType
from memory_stack import VirtualStackHelper
from opcodes import OpcodeList
from singleton import Singleton

ADDRESS_LENGTH = 32
FRAME_SERVICE_ATOMS = 3
assert 32 >= ADDRESS_LENGTH >= 1
assert FRAME_SERVICE_ATOMS >= 2


class Generator:
    opcodes: OpcodeList

    def __init__(self, ast: AST):
        self.opcodes: OpcodeList = OpcodeList(ADDRESS_LENGTH)

        # Init Virtual stack and function Singletons
        VirtualStackHelper(ADDRESS_LENGTH, FRAME_SERVICE_ATOMS).init_stack(self.opcodes)
        SpecialForms(ADDRESS_LENGTH)
        BuiltIns(ADDRESS_LENGTH)

        # Set jump to main program body
        self.opcodes.add('PUSH', dec_to_hex(0, 2 * ADDRESS_LENGTH))
        jump_to_prog_start_i = len(self.opcodes.list) - 1
        self.opcodes.add('JUMP')

        for el in ast.root.child_nodes:
            context = Context(FRAME_SERVICE_ATOMS)

            if el.child_nodes[0].value == 'prog':
                context.is_prog = True
                # Jump from header to prog body
                self.opcodes.add('JUMPDEST')
                self.opcodes.list[jump_to_prog_start_i].extra_value = dec_to_hex(self.opcodes.list[-1].id,
                                                                                 2 * ADDRESS_LENGTH)

                self.opcodes.add('PUSH', dec_to_hex(0, 2 * ADDRESS_LENGTH))
                prog_atom_count = len(self.opcodes.list) - 1
                VirtualStackHelper().load_cur_atom_counter_addr(self.opcodes)
                self.opcodes.add('MSTORE')

                process_code_block(el.child_nodes[1], context, self.opcodes)

                self.opcodes.list[prog_atom_count].extra_value = dec_to_hex(context.counter - FRAME_SERVICE_ATOMS,
                                                                            2 * ADDRESS_LENGTH)

            else:
                Declared.declare(el, context, self.opcodes)

    def __validate(self, code: str):
        # ToDo: make normal ByteCode validation
        return True

    def get_byte_code(self):
        byte_code = self.opcodes.get_str()
        assert self.__validate(byte_code)
        return byte_code


def process_code_block(prog_body: AstNode, ctx: Context, opcodes: OpcodeList):
    # assert prog_body.type == AstNodeType.List
    for call in prog_body.child_nodes:
        process_call(call, ctx, opcodes)


def process_call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    # Processing syntax features: literals, atoms
    if call_body.type == AstNodeType.Literal:
        return process_literal(call_body, opcodes)

    if call_body.type == AstNodeType.Atom:
        return process_atom(call_body, ctx, opcodes)

    # Processing block of code
    if call_body.type == AstNodeType.List and call_body.child_nodes[0].type == AstNodeType.List:
        return process_code_block(call_body, ctx, opcodes)

    # Processing pre-built functions
    name = call_body.child_nodes[0].value

    # If we have a special form incoming, we delegate full processing to it
    if SpecialForms().has(name):
        return SpecialForms().call(call_body, ctx, opcodes)

    # Else we prepare an arguments and calls a function
    for i in range(1, len(call_body.child_nodes)):
        process_call(call_body.child_nodes[i], ctx, opcodes)

    if BuiltIns().has(name):
        return BuiltIns().call(call_body, ctx, opcodes)

    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_literal(call_body: AstNode, opcodes: OpcodeList):
    assert call_body.type == AstNodeType.Literal
    value = dec_to_hex(call_body.value, 2 * ADDRESS_LENGTH)
    opcodes.add('PUSH', value)


def process_atom(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    assert call_body.type == AstNodeType.Atom
    atom_name = call_body.value
    atom_address, is_new = ctx.get_atom_addr(atom_name)
    VirtualStackHelper().load_atom_value(opcodes, atom_address)


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

    def call(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        self.__funcs[body.child_nodes[0].value](self, body, ctx, opcodes)

    def __cond(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (0): | EoS |
        """
        assert len(body.child_nodes) == 3 or len(body.child_nodes) == 4

        # Conditions check
        process_call(body.child_nodes[1], ctx, opcodes)
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
        process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('PUSH', )
        jump_from_true_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # FALSE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_false].extra_value = dec_to_hex(block_id, 2 * self.address_length)
        if len(body.child_nodes) == 4:
            process_call(body.child_nodes[3], ctx, opcodes)
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

    def __while(self, body: AstNode, ctx: Context, opcodes: OpcodeList):
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
        process_call(body.child_nodes[1], ctx, opcodes)
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
        process_call(body.child_nodes[2], ctx, opcodes)
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


class Declared:
    addr_by_name: dict = {}

    @staticmethod
    def call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        assert call_body.type == AstNodeType.List
        assert call_body.child_nodes[0].type == AstNodeType.Literal or call_body.child_nodes[0].type == AstNodeType.Atom

        # Prepare arguments
        for i in range(1, len(call_body.child_nodes)):
            process_call(call_body.child_nodes[i], ctx, opcodes)

        # Prepare back address, part 1
        opcodes.add('PUSH')
        back_address = len(opcodes.list) - 1

        # Jump into the function
        opcodes.add('PUSH', dec_to_hex(Declared.addr_by_name[call_body.child_nodes[0].value], 2 * ADDRESS_LENGTH))
        opcodes.add('JUMP')

        # Prepare back address, part 2
        opcodes.add('JUMPDEST')
        opcodes.list[back_address].extra_value = dec_to_hex(opcodes.list[-1].id, 2 * ADDRESS_LENGTH)

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
        process_call(call_body.child_nodes[3], ctx, opcodes)

        # Set atom counter, part 2
        opcodes.list[func_atom_counter].extra_value = dec_to_hex(ctx.counter - FRAME_SERVICE_ATOMS, 2 * ADDRESS_LENGTH)

        # Remove frame and leave function
        VirtualStackHelper().load_back_address(opcodes)
        VirtualStackHelper().remove_frame(opcodes)
        opcodes.add('JUMP')


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





