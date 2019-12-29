from typing import Any, List
import logging
import sys

from AST import AST, AstNode, AstNodeType

logging.basicConfig(level=logging.DEBUG, filename=sys.stdout)

logger = logging.getLogger('Code_Generator')
logger.setLevel(logging.INFO)

ADDRESS_LENGTH = 2
FRAME_SERVICE_ATOMS = 3
assert 32 >= ADDRESS_LENGTH >= 1
assert FRAME_SERVICE_ATOMS >= 2

getInstructionCode = {
    'STOP': '00',
    'ADD': '01',
    'MUL': '02',
    'SUB': '03',
    'DIV': '04',
    'MOD': '06',
    'ADDMOD': '08',
    'MULMOD': '09',
    'EXP': '0a',
    'LT': '10',
    'GT': '11',
    'SLT': '12',
    'SGT': '13',
    'EQ': '14',
    'ISZERO': '15',
    'AND': '16',
    'OR': '17',
    'XOR': '18',
    'NOT': '19',
    'CALLDATALOAD': '35',
    'MLOAD': '51',
    'MSTORE': '52',
    'JUMP': '56',
    'JUMPI': '57',
    'JUMPDEST': '5b',
    'PUSH': hex(0x60 + ADDRESS_LENGTH - 1)[2:],
    'DUP1': '80',
    'DUP2': '81',
    'SWAP1': '90',
    'RETURN': 'f3'
}


def dec_to_hex(number: int, pad: int = 2 * ADDRESS_LENGTH):
    return '0x{0:0{1}X}'.format(number, pad)[2:]


opcodes_counter = 0


class Opcode:
    id: int
    name: str
    extra_value: Any

    def __init__(self, name: str, extra_value=None):
        global opcodes_counter
        self.id = opcodes_counter
        opcodes_counter += 1
        self.name = name
        if extra_value is not None:
            self.extra_value = extra_value
        elif name == 'PUSH':
            self.extra_value = dec_to_hex(0)
        else:
            self.extra_value = None
        if name == 'PUSH':
            opcodes_counter += ADDRESS_LENGTH

    def get_str(self):
        return f'{getInstructionCode[self.name]}{"" if self.name != "PUSH" else self.extra_value}'


class OpcodeList:
    list: List[Opcode]

    def __init__(self):
        self.list = []

    def add(self, name: str, extra_value=None):
        self.list.append(Opcode(name, extra_value))
        assert self.list[-1].id <= 255 ** ADDRESS_LENGTH

    def get_str(self):
        res = ''
        for oc in self.list:
            res += oc.get_str()
        return res


class Context:
    counter: int
    nameByNum: dict
    numByName: dict
    is_prog: bool = False

    def __init__(self):
        # ZERO reserved for prev gap
        # ONE reserved for atom countere
        # TWO reserved for back address
        self.counter = FRAME_SERVICE_ATOMS
        self.nameByNum = {}
        self.numByName = {}

    def get_atom_addr(self, name: str):
        is_added = False
        if name not in self.numByName:
            is_added = True
            self.numByName[name] = self.counter
            self.nameByNum[self.counter] = name
            self.counter += 1
        return self.numByName[name] * 32, is_added


def generate_code(ast: AST):
    opcodes: OpcodeList = OpcodeList()

    logger.info("Building the code...")

    VirtualStackHelper.init_stack(opcodes)

    # Set jump to main program body
    opcodes.add('PUSH', dec_to_hex(0))
    jump_to_prog_start_i = len(opcodes.list) - 1
    opcodes.add('JUMP')

    logger.info("Contract header generated...")

    for el in ast.root.child_nodes:
        context = Context()

        if el.child_nodes[0].value == 'prog':
            logger.info("Building prog..")

            context.is_prog = True
            # Jump from header to prog body
            opcodes.add('JUMPDEST')
            opcodes.list[jump_to_prog_start_i].extra_value = dec_to_hex(opcodes.list[-1].id)

            opcodes.add('PUSH', dec_to_hex(0))
            prog_atom_count = len(opcodes.list) - 1
            VirtualStackHelper.load_cur_atom_counter_addr(opcodes)
            opcodes.add('MSTORE')

            process_code_block(el.child_nodes[1], context, opcodes)

            opcodes.list[prog_atom_count].extra_value = dec_to_hex(context.counter - FRAME_SERVICE_ATOMS)

            logger.info("Prog has been built.")
        else:
            assert el.child_nodes[0].value == 'func'
            logger.info(f'Building func {el.child_nodes[1].value}')
            Declared.declare(el, context, opcodes)

    print_readable_code(opcodes)
    return opcodes.get_str()


def print_readable_code(opcodes: OpcodeList):
    filename = 'generated_code.ebc'
    logger.info("Generating readable disassemble")
    code_output = open(filename, 'w+')
    for opcode in opcodes.list:
        res = f"{dec_to_hex(opcode.id)}: {getInstructionCode[opcode.name]} "
        res += f"{('  ' * ADDRESS_LENGTH) if opcode.name != 'PUSH' else opcode.extra_value} "
        res += f"{opcode.name}"
        if opcode.name == 'PUSH':
            res += f" 0x{opcode.extra_value}"
        res += '\n'
        code_output.write(res)
    code_output.flush()
    code_output.close()
    logger.info(f"Readable disassemble available in {filename}")


def process_code_block(prog_body: AstNode, ctx: Context, opcodes: OpcodeList):
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
    if name == 'read':
        return BuiltIns.read(call_body, opcodes)
    elif name == 'break':
        return BuiltIns.bbreak(call_body, ctx, opcodes)
    elif name == 'cond':
        return BuiltIns.cond(call_body, ctx, opcodes)
    elif name == 'return':
        return BuiltIns.rreturn(call_body, ctx, opcodes)
    elif name == 'setq':
        return BuiltIns.setq(call_body, ctx, opcodes)
    elif name == 'while':
        return BuiltIns.wwhile(call_body, ctx, opcodes)
    elif name == 'plus':
        return BuiltIns.plus(call_body, ctx, opcodes)
    elif name == 'minus':
        return BuiltIns.minus(call_body, ctx, opcodes)
    elif name == 'times':
        return BuiltIns.times(call_body, ctx, opcodes)
    elif name == 'divide':
        return BuiltIns.divide(call_body, ctx, opcodes)
    elif name == 'equal':
        return BuiltIns.equal(call_body, ctx, opcodes)
    elif name == 'nonequal':
        return BuiltIns.nonequal(call_body, ctx, opcodes)
    elif name == 'less':
        return BuiltIns.less(call_body, ctx, opcodes)
    elif name == 'lesseq':
        return BuiltIns.lesseq(call_body, ctx, opcodes)
    elif name == 'greater':
        return BuiltIns.greater(call_body, ctx, opcodes)
    elif name == 'greaterq':
        return BuiltIns.greatereq(call_body, ctx, opcodes)
    elif name == 'or':
        return BuiltIns.oor(call_body, ctx, opcodes)
    elif name == 'and':
        return BuiltIns.aand(call_body, ctx, opcodes)
    elif name == 'not':
        return BuiltIns.nnot(call_body, ctx, opcodes)

    if name in Declared.addr_by_name:
        return Declared.call(call_body, ctx, opcodes)

    print(f'No builtin found for {name}')

    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_literal(call_body: AstNode, opcodes: OpcodeList):
    value = dec_to_hex(call_body.value)
    opcodes.add('PUSH', value)


def process_atom(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    atom_name = call_body.value
    atom_address, is_new = ctx.get_atom_addr(atom_name)
    VirtualStackHelper.load_atom_value(opcodes, atom_address)


class Declared:
    addr_by_name: dict = {}

    @staticmethod
    def call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        # Prepare arguments
        for i in range(1, len(call_body.child_nodes)):
            process_call(call_body.child_nodes[i], ctx, opcodes)

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
        process_call(call_body.child_nodes[3], ctx, opcodes)

        # Set atom counter, part 2
        opcodes.list[func_atom_counter].extra_value = dec_to_hex(ctx.counter - FRAME_SERVICE_ATOMS)

        # Remove frame and leave function
        VirtualStackHelper.load_back_address(opcodes)
        VirtualStackHelper.remove_frame(opcodes)
        opcodes.add('JUMP')


class BuiltIns:
    @staticmethod
    def read(body: AstNode, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (1): | EoS | Value from input
        """
        arg_num = body.child_nodes[1].value * 32
        offset = dec_to_hex(arg_num)
        opcodes.add('PUSH', offset)
        opcodes.add('CALLDATALOAD')

    @staticmethod
    def cond(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (0): | EoS |
        """
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
        opcodes.list[jump_from_check_to_true].extra_value = dec_to_hex(block_id)
        process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('PUSH', )
        jump_from_true_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # FALSE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_false].extra_value = dec_to_hex(block_id)
        if len(body.child_nodes) == 4:
            process_call(body.child_nodes[3], ctx, opcodes)
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
        process_call(body.child_nodes[2], ctx, opcodes)
        """
        INPUT  (1): | EoS | New Atom value
        OUTPUT (0): | EoS |
        """
        atom_name = body.child_nodes[1].value
        address, is_new = ctx.get_atom_addr(atom_name)
        VirtualStackHelper.store_atom_value(opcodes, address)

    @staticmethod
    def equal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Does value 1 equals value 2 (bool)
        """
        opcodes.add('EQ')

    @staticmethod
    def nonequal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Does Value 1 differs from Value 2 (bool)
        """
        opcodes.add('EQ')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('EQ')

    @staticmethod
    def nnot(body: AstNode, ctx: Context, opcodes: OpcodeList):
        process_call(body.child_nodes[1], ctx, opcodes)
        """
        INPUT  (1): | EoS | value (bool)
        OUTPUT (1): | EoS | !value (bool)
        """
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('EQ')

    @staticmethod
    def plus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Sum of values
        """
        opcodes.add('ADD')

    @staticmethod
    def minus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Value 1 - Value 2
        """
        opcodes.add('SWAP1')
        opcodes.add('SUB')

    @staticmethod
    def times(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Value 1 * Value 2
        """
        opcodes.add('MUL')

    @staticmethod
    def divide(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Value 1 // Value 2
        """
        opcodes.add('SWAP1')
        opcodes.add('DIV')

    @staticmethod
    def rreturn(body: AstNode, ctx: Context, opcodes: OpcodeList):
        process_call(body.child_nodes[1], ctx, opcodes)
        """
        INPUT  (1): | EoS | Some value 
        OUTPUT (0): | EoS | 
        """

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
    current_while = None

    @staticmethod
    def bbreak(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('JUMP', dec_to_hex(BuiltIns.current_while))
        pass

    @staticmethod
    def wwhile(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        prev_while = BuiltIns.current_while
        BuiltIns.current_while = BuiltIns.while_count
        BuiltIns.while_count += 1
        opcodes.add('JUMPDEST', dec_to_hex(BuiltIns.current_while))
        jumpdest_to_condition_check_id = dec_to_hex(opcodes.list[-1].id)
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
        opcodes.list[jump_to_while_body].extra_value = dec_to_hex(opcodes.list[-1].id)
        process_call(body.child_nodes[2], ctx, opcodes)
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
        process_call(body.child_nodes[1], ctx, opcodes)
        process_call(body.child_nodes[2], ctx, opcodes)
        # | n | b | EOS |
        # b < n
        opcodes.add('GT')

    @staticmethod
    def lesseq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        process_call(body.child_nodes[1], ctx, opcodes)
        process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('EQ')
        process_call(body.child_nodes[1], ctx, opcodes)
        process_call(body.child_nodes[2], ctx, opcodes)
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
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Is Value 1 greater than Value 2
        """
        opcodes.add('LT')


    @staticmethod
    def greatereq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        process_call(body.child_nodes[1], ctx, opcodes)
        process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('EQ')
        process_call(body.child_nodes[1], ctx, opcodes)
        process_call(body.child_nodes[2], ctx, opcodes)
        # | n | b | EOS |
        # b < n
        opcodes.add('LT')
        opcodes.add('OR')

    @staticmethod
    def oor(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool) 
        OUTPUT (1): | EoS | v1 OR v2 (bool)
        """
        opcodes.add('OR')

    @staticmethod
    def aand(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool) 
        OUTPUT (1): | EoS | v1 AND v2 (bool)
        """
        opcodes.add('AND')


'''
Global memory description:
0x00: Start of current frame AKA CURRENT GAP
0x20: Temporary register (eg. for swaps)
0x40: Start of ZERO FRAME

Frame memory description:
GAP + 0x00: Start of previout frame
GAP + 0x20: Counter of atoms on frame
GAP + 0x40: Address of caller's JUMPDEST (for functions) AKA BACK ADDRESS
GAP + 0x60: Start of stack memory

Symbols:
EoS - End of Stack
'''


class VirtualStackHelper:
    @staticmethod
    def init_stack(opcodes: OpcodeList):
        """
        NO SIDE EFFECTS
        """
        # Set ZERO FRAME (prog frame) gap = 0x40
        opcodes.add('PUSH', dec_to_hex(0x40))
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MSTORE')
        # Init zero frame
        # Set start of previous frame and back address as 0x00
        opcodes.add('PUSH', dec_to_hex(0x0))
        opcodes.add('DUP1')
        opcodes.add('PUSH', dec_to_hex(0x40))
        opcodes.add('MSTORE')
        opcodes.add('PUSH', dec_to_hex(0x40 + 0x40))
        opcodes.add('MSTORE')
        # Set counter of atoms as 0x00
        opcodes.add('PUSH', dec_to_hex(0x0))
        opcodes.add('PUSH', dec_to_hex(0x40 + 0x20))
        opcodes.add('MSTORE')

    @staticmethod
    def store_atom_value(opcodes: OpcodeList, atom_address: int):
        """
        INPUT:  | EoS | New value of Atom
        OUTPUT: | EoS |
        """
        VirtualStackHelper.load_atom_address(opcodes, atom_address)
        opcodes.add('MSTORE')

    @staticmethod
    def load_atom_address(opcodes: OpcodeList, atom_address: int):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of Atom on provided address
        """
        VirtualStackHelper.load_cur_gap(opcodes)
        opcodes.add('PUSH', dec_to_hex(atom_address))
        opcodes.add('ADD')

    @staticmethod
    def load_atom_value(opcodes: OpcodeList, atom_address: int):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Value of Atom on provided address |
        """
        VirtualStackHelper.load_atom_address(opcodes, atom_address)
        opcodes.add('MLOAD')

    @staticmethod
    def load_cur_gap(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Gap of current frame |
        """
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')

    @staticmethod
    def store_new_gap(opcodes: OpcodeList):
        """
        INPUT:  | EoS | New gap
        OUTPUT: | EoS |
        """
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MSTORE')

    @staticmethod
    def load_prev_gap(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of previout frame's start
        """
        VirtualStackHelper.load_cur_gap(opcodes)
        opcodes.add('MLOAD')

    @staticmethod
    def load_cur_atom_counter_addr(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of Current Atom counter
        """
        VirtualStackHelper.load_cur_gap(opcodes)
        opcodes.add('PUSH', dec_to_hex(0x20))
        opcodes.add('ADD')

    @staticmethod
    def load_cur_atom_counter(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Value of Current Atom counter
        """
        VirtualStackHelper.load_cur_atom_counter_addr(opcodes)
        opcodes.add('MLOAD')

    @staticmethod
    def load_back_address_addr(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of Current Back address
        """
        VirtualStackHelper.load_cur_gap(opcodes)
        opcodes.add('PUSH', dec_to_hex(0x40))
        opcodes.add('ADD')

    @staticmethod
    def load_back_address(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Current Back address
        """
        VirtualStackHelper.load_back_address_addr(opcodes)
        opcodes.add('MLOAD')

    @staticmethod
    def store_back_address(opcodes: OpcodeList):
        """
        INPUT:  | EoS | New Back address
        OUTPUT: | EoS |
        """
        VirtualStackHelper.load_back_address_addr(opcodes)
        opcodes.add('MSTORE')

    @staticmethod
    def calc_cur_frame_size(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Size of current frame
        """
        opcodes.add('PUSH', dec_to_hex(FRAME_SERVICE_ATOMS * 0x20))

        VirtualStackHelper.load_cur_atom_counter(opcodes)
        opcodes.add('PUSH', dec_to_hex(32))
        opcodes.add('MUL')

        opcodes.add('ADD')

    @staticmethod
    def calc_new_frame_gap(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Gap of new frame
        """
        VirtualStackHelper.load_cur_gap(opcodes)
        VirtualStackHelper.calc_cur_frame_size(opcodes)
        opcodes.add('ADD')

    @staticmethod
    def add_frame(opcodes: OpcodeList):
        """
        INPUT:  | EoS | Arg1 | ... | ArgN | Back Address |
        OUTPUT: | EoS | Arg1 | ... | ArgN |
        """
        VirtualStackHelper.load_cur_gap(opcodes)
        VirtualStackHelper.calc_new_frame_gap(opcodes)
        opcodes.add('MSTORE')

        VirtualStackHelper.calc_new_frame_gap(opcodes)
        VirtualStackHelper.store_new_gap(opcodes)

        # Back address gone
        VirtualStackHelper.store_back_address(opcodes)

    @staticmethod
    def remove_frame(opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        VirtualStackHelper.load_prev_gap(opcodes)
        VirtualStackHelper.store_new_gap(opcodes)
