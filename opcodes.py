from typing import Any, List

from dec_to_hex import dec_to_hex


class Opcode:
    id: int
    name: str
    extra_value: Any
    __counter = 0
    __instruction_set: dict = None

    def __init__(self, name: str, address_length: int, extra_value=None, instruction_set: dict = None):
        self.id = Opcode.__counter
        self.__instruction_set = instruction_set
        Opcode.__counter += 1
        self.name = name
        if extra_value is not None:
            self.extra_value = extra_value
        elif name == 'PUSH':
            self.extra_value = dec_to_hex(0, 2 * address_length)
        else:
            self.extra_value = None
        if name == 'PUSH':
            Opcode.__counter += address_length

    def get_str(self):
        return f'{self.__instruction_set[self.name]}{"" if self.name != "PUSH" else self.extra_value}'

    @staticmethod
    def reset_counter():
        Opcode.__counter = 0


class OpcodeList:
    list: List[Opcode]
    address_length: int

    def __init__(self, address_length):
        self.list = []
        self.address_length = address_length
        self.getInstructionCode = {
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
        'PUSH': hex(0x60 + address_length - 1)[2:],
        'DUP1': '80',
        'DUP2': '81',
        'SWAP1': '90',
        'RETURN': 'f3'
    }

    def add(self, name: str, extra_value=None):
        self.list.append(Opcode(name, self.address_length, extra_value, self.getInstructionCode))

    def get_str(self):
        res = ''
        for oc in self.list:
            res += oc.get_str()
        return res