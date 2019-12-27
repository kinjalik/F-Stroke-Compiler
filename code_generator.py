from typing import Any, List
import logging
import sys

from AST import AST, AstNode, AstNodeType

logging.basicConfig(level=logging.DEBUG, filename=sys.stdout)

logger = logging.getLogger('Code_Generator')
logger.setLevel(logging.INFO)

ADDRESS_LENGTH = 2
assert 32 >= ADDRESS_LENGTH >= 1

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
        self.counter = 3
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
    # Initialize stack memory with zero frame starting on 0x20
    opcodes.add('PUSH', dec_to_hex(32))
    opcodes.add('PUSH', dec_to_hex(0))
    opcodes.add('MSTORE')

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
            opcodes.add('JUMPDEST')
            opcodes.list[jump_to_prog_start_i].extra_value = dec_to_hex(opcodes.list[-1].id)
            process_code_block(el.child_nodes[1], context, opcodes)
            logger.info("Prog has been built.")
        else:
            assert el.child_nodes[0].value == 'func'
            Declared.declare_dunction(el, context, opcodes)
        del context
    print_readable_code(opcodes)
    return opcodes.get_str()


def print_readable_code(opcodes: OpcodeList):
    filename = 'generated_code.ebc'
    logger.info("Generating readable disassembly")
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
    logger.info(f"Readable disassembly availiable in {filename}")


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
    elif name == 'equal':
        return BuiltIns.equal(call_body, ctx, opcodes)
    elif name == 'nonequal':
        return BuiltIns.nonequal(call_body, ctx, opcodes)
    elif name == 'not':
        return BuiltIns.nnot(call_body, ctx, opcodes)
    elif name == 'lesseq':
        return BuiltIns.lesseq(call_body, ctx, opcodes)
    elif name == 'plus':
        return BuiltIns.plus(call_body, ctx, opcodes)
    elif name == 'minus':
        return BuiltIns.minus(call_body, ctx, opcodes)
    elif name == 'times':
        return BuiltIns.times(call_body, ctx, opcodes)
    elif name == 'divide':
        return BuiltIns.divide(call_body, ctx, opcodes)
    elif name == 'while':
        return BuiltIns.wwhile(call_body, ctx, opcodes)
    elif name == 'greater':
        return BuiltIns.greater(call_body, ctx, opcodes)
    elif name == 'less':
        return BuiltIns.less(call_body, ctx, opcodes)
    elif name == 'or':
        return BuiltIns.oor(call_body, ctx, opcodes)
    elif name == 'and':
        return BuiltIns.aand(call_body, ctx, opcodes)

    if name in Declared.function_addresses:
        return process_declared_call(call_body, ctx, opcodes)

    print(f'No builtin or decl found for {name}')

    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_declared_call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    for i in range(1, len(call_body.child_nodes)):
        process_call(call_body.child_nodes[i], ctx, opcodes)

    opcodes.add('PUSH')
    back_address = len(opcodes.list) - 1

    opcodes.add('PUSH', dec_to_hex(Declared.function_addresses[call_body.child_nodes[0].value]))
    opcodes.add('JUMP')
    opcodes.add('JUMPDEST')
    opcodes.list[back_address].extra_value = dec_to_hex(opcodes.list[-1].id)


def process_literal(call_body: AstNode, opcodes: OpcodeList):
    value = dec_to_hex(call_body.value)
    opcodes.add('PUSH', value)


def process_atom(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    atom_name = call_body.value
    atom_address, is_new = ctx.get_atom_addr(atom_name)
    opcodes.add('PUSH', dec_to_hex(atom_address))
    opcodes.add('PUSH', dec_to_hex(0))
    opcodes.add('MLOAD')
    opcodes.add('ADD')
    opcodes.add('MLOAD')


class BuiltIns:
    @staticmethod
    def read(body: AstNode, opcodes: OpcodeList):
        arg_num = body.child_nodes[1].value * 32
        offset = dec_to_hex(arg_num)
        opcodes.add('PUSH', offset)
        opcodes.add('CALLDATALOAD')

    @staticmethod
    def cond(body: AstNode, ctx: Context, opcodes: OpcodeList):
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
        atom_name = body.child_nodes[1].value
        process_call(body.child_nodes[2], ctx, opcodes)
        address, is_new = ctx.get_atom_addr(atom_name)
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('PUSH', dec_to_hex(address))
        opcodes.add('ADD')
        opcodes.add('MSTORE')
        if is_new:
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MLOAD')
            opcodes.add('PUSH', dec_to_hex(0x20))
            opcodes.add('ADD')
            opcodes.add('MLOAD')
            opcodes.add('PUSH', dec_to_hex(1))
            opcodes.add('ADD')
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MLOAD')
            opcodes.add('PUSH', dec_to_hex(0x20))
            opcodes.add('ADD')
            opcodes.add('MSTORE')


    @staticmethod
    def equal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('EQ')

    @staticmethod
    def nonequal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('EQ')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('EQ')

    @staticmethod
    def nnot(body: AstNode, ctx: Context, opcodes: OpcodeList):
        process_call(body.child_nodes[1], ctx, opcodes)
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('EQ')

    @staticmethod
    def plus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('ADD')

    @staticmethod
    def minus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('SWAP1')
        opcodes.add('SUB')

    @staticmethod
    def times(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('MUL')

    @staticmethod
    def divide(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('SWAP1')
        opcodes.add('DIV')

    @staticmethod
    def rreturn(body: AstNode, ctx: Context, opcodes: OpcodeList):
        process_call(body.child_nodes[1], ctx, opcodes)

        # opcodes.add('PUSH', dec_to_hex(32))
        # opcodes.add('PUSH', dec_to_hex(32 * 2))
        # opcodes.add('RETURN')

        if ctx.is_prog:
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MSTORE')
            opcodes.add('PUSH', dec_to_hex(32))
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('RETURN')
        else:
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MLOAD')
            opcodes.add('PUSH', dec_to_hex(0x40))
            opcodes.add('ADD')
            opcodes.add('MLOAD')

            # set prev gap back
            opcodes.add('PUSH', dec_to_hex(0x40))
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MLOAD')
            opcodes.add('ADD')
            opcodes.add('MLOAD')
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MSTORE')

            opcodes.add('JUMP')

    while_count = 0
    current_while = None

    @staticmethod
    def bbreak(body: AstNode, ctx: Context, opcodes: OpcodeList):
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('JUMP', dec_to_hex(BuiltIns.current_while))
        pass

    @staticmethod
    def wwhile(body: AstNode, ctx: Context, opcodes: OpcodeList):
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
    def lesseq(body: AstNode, ctx: Context, opcodes: OpcodeList):
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
        opcodes.add('LT')

    @staticmethod
    def less(body: AstNode, ctx: Context, opcodes: OpcodeList):
        process_call(body.child_nodes[1], ctx, opcodes)
        process_call(body.child_nodes[2], ctx, opcodes)
        # | n | b | EOS |
        # b < n
        opcodes.add('GT')

    @staticmethod
    def oor(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('OR')

    @staticmethod
    def aand(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('AND')


class Declared:
    function_addresses = {}

    @staticmethod
    def get_func_addr(name: str):
        return Declared.function_addresses[name]

    @staticmethod
    def declare_dunction(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
        opcodes.add('JUMPDEST')
        Declared.function_addresses[call_body.child_nodes[1].value] = opcodes.list[-1].id

        # calc cur gap
        opcodes.add('PUSH', dec_to_hex(0x60))
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('PUSH', dec_to_hex(0x20))
        opcodes.add('ADD')
        opcodes.add('MLOAD')
        opcodes.add('ADD')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('ADD')

        # load prev gap
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('SWAP1')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MSTORE')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('MSTORE')

        # load back address
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('PUSH', dec_to_hex(0x40))
        opcodes.add('ADD')
        opcodes.add('MSTORE')

        # Load variables
        for arg in reversed(call_body.child_nodes[2].child_nodes):
            assert arg.type == AstNodeType.Atom
            address, is_new = ctx.get_atom_addr(arg.value)
            opcodes.add('PUSH', dec_to_hex(0))
            opcodes.add('MLOAD')
            opcodes.add('PUSH', dec_to_hex(address))
            opcodes.add('ADD')
            opcodes.add('MSTORE')

        process_call(call_body.child_nodes[3], ctx, opcodes)

        # load back address
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('PUSH', dec_to_hex(0x40))
        opcodes.add('ADD')
        opcodes.add('MLOAD')

        # set prev gap back
        opcodes.add('PUSH', dec_to_hex(0x40))
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MLOAD')
        opcodes.add('ADD')
        opcodes.add('MLOAD')
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('MSTORE')

        opcodes.add('JUMP')