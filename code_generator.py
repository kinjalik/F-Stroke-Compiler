from typing import Any, List

from AST import AST, AstNode, AstNodeType

ADDRESS_LENGTH = 32
assert ADDRESS_LENGTH <= 32

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
        return f'{getInstructionCode[self.name]}{"" if self.extra_value is None else self.extra_value}'


class OpcodeList:
    list: List[Opcode]

    def __init__(self):
        self.list = []

    def add(self, name: str, extra_value=None):
        self.list.append(Opcode(name, extra_value))

    def get_str(self):
        res = ''
        for oc in self.list:
            res += oc.get_str()
        return res


class ContextFactory:
    addrs_used: set

    def __init__(self):
        self.addrs_used = set()

    def create_context(self):
        return Context(self)

    def take_address(self):
        i = 1
        while i in self.addrs_used:
            i += 1
        self.addrs_used.add(i)
        return i

    def free_address(self, number: int):
        assert number in self.addrs_used
        self.addrs_used.remove(number)


class Context:
    nameByNum: dict
    numByName: dict
    factory: ContextFactory

    def __init__(self, factory: ContextFactory):
        self.nameByNum = {}
        self.numByName = {}
        self.factory = factory

    def get_atom_addr(self, name: str):
        if name in self.numByName:
            return dec_to_hex(self.numByName[name] * 32)
        number = self.factory.take_address()
        self.nameByNum[number] = name
        self.numByName[name] = number
        return dec_to_hex(number * 32)

    def __del__(self):
        for name, number in self.numByName.items():
            self.factory.free_address(number)


def generate_code(ast: AST):
    opcodes: OpcodeList = OpcodeList()
    context_factory = ContextFactory()
    for el in ast.root.child_nodes:
        context = context_factory.create_context()
        if el.child_nodes[0].value == 'prog':
            process_code_block(el.child_nodes[1], context, opcodes)
            print('PROG DECLARED')
        else:
            # ToDo: Function declaration
            print('FUNC DECLARED')
    print_readable_code(opcodes)
    return opcodes.get_str()


def print_readable_code(opcodes: OpcodeList):
    code_output = open('generated_code.ebc', 'w+')
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


def process_code_block(prog_body: AstNode, ctx: Context, opcodes: OpcodeList):
    for call in prog_body.child_nodes:
        print(call.to_dict())
        process_call(call, ctx, opcodes)


def process_call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    # Processing syntax features: literals, atoms
    if call_body.type == AstNodeType.Literal:
        return process_literal(call_body, ctx, opcodes)

    if call_body.type == AstNodeType.Atom:
        return process_atom(call_body, ctx, opcodes)

    # Processing block of code
    if call_body.type == AstNodeType.List and call_body.child_nodes[0].type == AstNodeType.List:
        return process_code_block(call_body, ctx, opcodes)

    # Processing pre-built functions
    name = call_body.child_nodes[0].value
    if name == 'read':
        return BuiltIns.read(call_body, ctx, opcodes)
    elif name == 'cond':
        return BuiltIns.cond(call_body, ctx, opcodes)
    elif name == 'return':
        return BuiltIns.rreturn(call_body, ctx, opcodes)
    elif name == 'setq':
        return BuiltIns.setq(call_body, ctx, opcodes)
    elif name == 'equal':
        return BuiltIns.equal(call_body, ctx, opcodes)
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
    print(f'No builtin found for {name}')
    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_literal(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    value = dec_to_hex(call_body.value)
    opcodes.add('PUSH', value)


def process_atom(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    atom_name = call_body.value
    atom_address = ctx.get_atom_addr(atom_name)
    opcodes.add('PUSH', atom_address)
    opcodes.add('MLOAD')


class BuiltIns:
    @staticmethod
    def read(body: AstNode, ctx: Context, opcodes: OpcodeList):
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
        address = ctx.get_atom_addr(atom_name)
        opcodes.add('PUSH', address)
        opcodes.add('MSTORE')

    @staticmethod
    def equal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
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
        opcodes.add('PUSH')
        opcodes.add('MSTORE')
        opcodes.add('PUSH', dec_to_hex(32))
        opcodes.add('PUSH')
        opcodes.add('RETURN')

    @staticmethod
    def wwhile(body: AstNode, ctx: Context, opcodes: OpcodeList):
        print(body)
        opcodes.add('JUMPDEST')
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
