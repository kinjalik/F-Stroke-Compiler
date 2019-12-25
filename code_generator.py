from typing import Any, List

from AST import AST, AstNode, AstNodeType

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
    'PUSH1': '60',
    'DUP1': '80',
    'SWAP1': '90',
    'RETURN': 'f3'
}

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
        self.extra_value = extra_value
        if name == 'PUSH1':
            opcodes_counter += 1

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


atom_counter = 0


class Context:
    addrByName: dict
    nameByAddr: dict

    def __init__(self):
        self.addrByName = {}
        self.nameByAddr = {}

    def add_atom(self, name: str):
        global atom_counter
        address = hex(atom_counter * 32)[2:]
        while len(address) != 2:
            address = '0' + address
        self.addrByName[name] = address
        self.nameByAddr[address] = name
        atom_counter += 1
        return address


def generate_code(ast: AST):
    atom_counter = 0
    opcode_counter = 0
    opcodes: OpcodeList = OpcodeList()
    for el in ast.root.child_nodes:
        context = Context()
        if el.child_nodes[0].value == 'prog':
            process_code_block(el.child_nodes[1], context, opcodes)
        else:
            # ToDo: Function declaration
            print('FUNC DECLARED')
    return opcodes.get_str()


def process_code_block(prog_body: AstNode, ctx: Context, opcodes: OpcodeList):
    for call in prog_body.child_nodes:
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
    elif name == 'plus':
        return BuiltIns.plus(call_body, ctx, opcodes)
    elif name == 'times':
        return BuiltIns.times(call_body, ctx, opcodes)
    elif name == 'divide':
        return BuiltIns.divide(call_body, ctx, opcodes)
    print(f'No builtin found for {name}')
    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_literal(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    value = '0x{0:0{1}X}'.format(int(call_body.value), 2)[2:]
    opcodes.add('PUSH1', value)


def process_atom(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    atom_name = call_body.value
    atom_address = ctx.addrByName[atom_name]
    opcodes.add('PUSH1', atom_address)
    opcodes.add('MLOAD')


class BuiltIns:
    @staticmethod
    def read(body: AstNode, ctx: Context, opcodes: OpcodeList):
        argNum = body.child_nodes[1].value * 32
        offset = '0x{0:0{1}X}'.format(argNum, 2)[2:]
        opcodes.add('PUSH1', offset)
        opcodes.add('CALLDATALOAD')

    @staticmethod
    def cond(body: AstNode, ctx: Context, opcodes: OpcodeList):
        # Conditions check
        process_call(body.child_nodes[1], ctx, opcodes)
        # JUMP TO TRUE
        opcodes.add('PUSH1', '00')
        jump_from_check_to_true = len(opcodes.list) - 1
        opcodes.add('JUMPI')
        # JUMP TO ELSE
        opcodes.add('PUSH1', '00')
        jump_from_check_to_false = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # TRUE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_true].extra_value = '0x{0:0{1}X}'.format(block_id, 2)[2:]
        process_call(body.child_nodes[2], ctx, opcodes)
        opcodes.add('PUSH1', '00')
        jump_from_true_to_end = len(opcodes.list) - 1
        opcodes.add('JUMP')
        # FALSE BLOCK
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_check_to_false].extra_value = '0x{0:0{1}X}'.format(block_id, 2)[2:]
        if len(body.child_nodes) == 4:
            process_call(body.child_nodes[3], ctx, opcodes)
        opcodes.add('PUSH1', '00')
        jump_from_false_to_end = len(opcodes.list) - 1
        # END
        opcodes.add('JUMPDEST')
        block_id = opcodes.list[-1].id
        opcodes.list[jump_from_true_to_end].extra_value = '0x{0:0{1}X}'.format(block_id, 2)[2:]
        opcodes.list[jump_from_false_to_end].extra_value = '0x{0:0{1}X}'.format(block_id, 2)[2:]

    @staticmethod
    def setq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        atomName = body.child_nodes[1].value
        process_call(body.child_nodes[2], ctx, opcodes)
        address = ctx.add_atom(atomName)
        opcodes.add('PUSH1', address)
        opcodes.add('MSTORE')

    @staticmethod
    def equal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        print(body.to_dict())
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('EQ')

    @staticmethod
    def plus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        opcodes.add('ADD')

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
        opcodes.add('PUSH1', '00')
        opcodes.add('MSTORE')
        opcodes.add('PUSH1', '20')
        opcodes.add('PUSH1', '00')
        opcodes.add('RETURN')
