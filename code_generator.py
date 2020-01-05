from typing import Any, List

from AST import AST, AstNode, AstNodeType
from singleton import Singleton, SingletonArgumentException
from fst_functions.builtin import BuiltIns
from fst_functions.declared import Declared

ADDRESS_LENGTH = 32
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


class Opcode:
    id: int
    name: str
    extra_value: Any
    __counter = 0

    def __init__(self, name: str, extra_value=None):
        self.id = Opcode.__counter
        Opcode.__counter += 1
        self.name = name
        if extra_value is not None:
            self.extra_value = extra_value
        elif name == 'PUSH':
            self.extra_value = dec_to_hex(0)
        else:
            self.extra_value = None
        if name == 'PUSH':
            Opcode.__counter += ADDRESS_LENGTH

    def get_str(self):
        return f'{getInstructionCode[self.name]}{"" if self.name != "PUSH" else self.extra_value}'

    @staticmethod
    def reset_counter():
        Opcode.__counter = 0


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


class ByteCodeGenerator(metaclass=Singleton):
    opcodes: OpcodeList
    ast: AST
    is_code_generated: bool = False

    def __init__(self, ast: AST):

        if ast is None:
            raise SingletonArgumentException('AST not provided to byte code generator')

        self.opcodes: OpcodeList = OpcodeList()
        VirtualStackHelper.init_stack(self.opcodes)
        self.ast = ast

    def run(self):
        # Set jump to main program body
        self.opcodes.add('PUSH', dec_to_hex(0))
        jump_to_prog_start_i = len(self.opcodes.list) - 1
        self.opcodes.add('JUMP')

        for el in self.ast.root.child_nodes:
            context = Context()

            if el.child_nodes[0].value == 'prog':
                context.is_prog = True
                # Jump from header to prog body
                self.opcodes.add('JUMPDEST')
                self.opcodes.list[jump_to_prog_start_i].extra_value = dec_to_hex(self.opcodes.list[-1].id)

                self.opcodes.add('PUSH', dec_to_hex(0))
                prog_atom_count = len(self.opcodes.list) - 1
                VirtualStackHelper.load_cur_atom_counter_addr(self.opcodes)
                self.opcodes.add('MSTORE')

                ByteCodeGenerator().process_code_block(el.child_nodes[1], context)

                self.opcodes.list[prog_atom_count].extra_value = dec_to_hex(context.counter - FRAME_SERVICE_ATOMS)

            else:
                Declared.declare(el, context, self.opcodes)

        self.is_code_generated = True
        return self

    @staticmethod
    def __validate(code: str):
        for c in code:
            if c not in '1234567890abcdefABCDEF':
                return False

        instruction_codes = [getInstructionCode[key] for key in getInstructionCode]

        i = 0
        while i < len(code):
            cur_code = code[i] + code[i + 1]
            i += 2
            if cur_code not in instruction_codes:
                return False
            if cur_code == getInstructionCode['PUSH']:
                i += 2 * ADDRESS_LENGTH

        return True

    def get_str(self):
        assert self.is_code_generated == True

        byte_code = self.opcodes.get_str()
        assert self.__validate(byte_code)
        return byte_code

    def process_code_block(self, prog_body: AstNode, ctx: Context):
        # assert prog_body.type == AstNodeType.List
        for call in prog_body.child_nodes:
            self.process_call(call, ctx)

    def process_call(self, call_body: AstNode, ctx: Context):
        # Processing syntax features: literals, atoms
        if call_body.type == AstNodeType.Literal:
            return self.process_literal(call_body)

        if call_body.type == AstNodeType.Atom:
            return self.process_atom(call_body, ctx)

        # Processing block of code
        if call_body.type == AstNodeType.List and call_body.child_nodes[0].type == AstNodeType.List:
            return self.process_code_block(call_body, ctx)

        # Processing pre-built functions
        name = call_body.child_nodes[0].value
        if name == 'read':
            return BuiltIns.read(call_body, ctx, self.opcodes)
        elif name == 'setq':
            return BuiltIns.setq(call_body, ctx, self.opcodes)
        elif name == 'cond':
            return BuiltIns.cond(call_body, ctx, self.opcodes)
        elif name == 'while':
            return BuiltIns.wwhile(call_body, ctx, self.opcodes)
        elif name == 'break':
            return BuiltIns.bbreak(call_body, ctx, self.opcodes)
        elif name == 'return':
            return BuiltIns.rreturn(call_body, ctx, self.opcodes)
        elif name == 'plus':
            return BuiltIns.plus(call_body, ctx, self.opcodes)
        elif name == 'minus':
            return BuiltIns.minus(call_body, ctx, self.opcodes)
        elif name == 'times':
            return BuiltIns.times(call_body, ctx, self.opcodes)
        elif name == 'divide':
            return BuiltIns.divide(call_body, ctx, self.opcodes)
        elif name == 'equal':
            return BuiltIns.equal(call_body, ctx, self.opcodes)
        elif name == 'nonequal':
            return BuiltIns.nonequal(call_body, ctx, self.opcodes)
        elif name == 'less':
            return BuiltIns.less(call_body, ctx, self.opcodes)
        elif name == 'lesseq':
            return BuiltIns.lesseq(call_body, ctx, self.opcodes)
        elif name == 'greater':
            return BuiltIns.greater(call_body, ctx, self.opcodes)
        elif name == 'greatereq':
            return BuiltIns.greatereq(call_body, ctx, self.opcodes)
        elif name == 'or':
            return BuiltIns.oor(call_body, ctx, self.opcodes)
        elif name == 'and':
            return BuiltIns.aand(call_body, ctx, self.opcodes)
        elif name == 'not':
            return BuiltIns.nnot(call_body, ctx, self.opcodes)

        if name in Declared.addr_by_name:
            return Declared.call(call_body, ctx, self.opcodes)

        # print(f'No builtin found for {name}')

        return 0
        # print(name)
        # for i in range(1, len(call_body.child_nodes)):
        #     arg = call_body.child_nodes[i]
        #     print(arg.type)

    def process_literal(self, call_body: AstNode):
        assert call_body.type == AstNodeType.Literal
        value = dec_to_hex(call_body.value)
        self.opcodes.add('PUSH', value)

    def process_atom(self, call_body: AstNode, ctx: Context):
        assert call_body.type == AstNodeType.Atom
        atom_name = call_body.value
        atom_address, is_new = ctx.get_atom_addr(atom_name)
        VirtualStackHelper.load_atom_value(self.opcodes, atom_address)


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
