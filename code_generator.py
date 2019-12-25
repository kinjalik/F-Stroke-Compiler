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
    'JUMP1': '57',
    'JUMPDEST': '5b',
    'PUSH1': '60',
    'DUP1': '80',
    'SWAP1': '90',
    'RETURN': 'f3'
}

atom_counter = 0
instructions_counter = 0


class Opcode:
    id: int
    name: str
    extra_value: Any

    def __init__(self, name: str, extra_value=None):
        global instructions_counter
        self.id = instructions_counter
        instructions_counter += 1
        self.name = name
        self.extra_value = extra_value

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
        self.addrByName['name'] = address
        self.nameByAddr[address] = name
        atom_counter += 1
        return address


def generate_code(ast: AST):
    atom_counter = 0
    opcode_counter = 0
    opcodes: OpcodeList = OpcodeList()
    for el in ast.root.child_nodes:
        if el.child_nodes[0].value == 'prog':
            process_prog(el.child_nodes[1], opcodes)
        else:
            # ToDo: Function declaration
            print('FUNC DECLARED')
    return opcodes.get_str()


def process_prog(prog_body: AstNode, opcodes: OpcodeList):
    context = Context()
    for call in prog_body.child_nodes:
        process_call(call, context, opcodes)
    print('Prog prcoessed')


def process_call(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    if call_body.type == AstNodeType.Literal:
        return process_literal(call_body, ctx, opcodes)
    name = call_body.child_nodes[0].value
    if name == 'read':
        return BuiltIns.read(call_body, ctx, opcodes)
    elif name == 'setq':
        return BuiltIns.setq(call_body, ctx, opcodes)
    elif name == 'plus':
        return BuiltIns.plus(call_body, ctx, opcodes)
    elif name == 'times':
        return BuiltIns.times(call_body, ctx, opcodes)
    elif name == 'divide':
        return BuiltIns.divide(call_body, ctx, opcodes)
    elif name == 'return':
        return BuiltIns.rreturn(call_body, ctx, opcodes)
    print(f'No builtin found for {name}')
    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_literal(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    value = '0x{0:0{1}X}'.format(int(call_body.value), 2)[2:]
    opcodes.add('PUSH1', value)


class BuiltIns:
    @staticmethod
    def read(body: AstNode, ctx: Context, opcodes: OpcodeList):
        argNum = body.child_nodes[1].value
        offset = '0x{0:0{1}X}'.format(argNum, 2)[2:]
        opcodes.add('PUSH1', offset)
        opcodes.add('CALLDATALOAD')

    @staticmethod
    def setq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        atomName = body.child_nodes[1].value
        process_call(body.child_nodes[2], ctx, opcodes)
        address = ctx.add_atom(atomName)
        opcodes.add('PUSH1', address)
        opcodes.add('MSTORE')

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
