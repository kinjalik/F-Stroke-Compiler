from utils import dec_to_hex
from opcodes import OpcodeList
from singleton import Singleton

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


class VirtualStackHelper(metaclass=Singleton):
    __address_length: int
    __frame_service_atoms: int

    def __init__(self, address_length, frame_service_atoms):
        self.__address_length = address_length
        self.__frame_service_atoms = frame_service_atoms

    def init_stack(self, opcodes: OpcodeList):
        """
        NO SIDE EFFECTS
        """
        # Set ZERO FRAME (prog frame) gap = 0x40
        opcodes.add('PUSH', dec_to_hex(0x40, 2 * self.__address_length))
        opcodes.add('PUSH', dec_to_hex(0, 2 * self.__address_length))
        opcodes.add('MSTORE')
        # Init zero frame
        # Set start of previous frame and back address as 0x00
        opcodes.add('PUSH', dec_to_hex(0x0, 2 * self.__address_length))
        opcodes.add('DUP1')
        opcodes.add('PUSH', dec_to_hex(0x40, 2 * self.__address_length))
        opcodes.add('MSTORE')
        opcodes.add('PUSH', dec_to_hex(0x40 + 0x40, 2 * self.__address_length))
        opcodes.add('MSTORE')
        # Set counter of atoms as 0x00
        opcodes.add('PUSH', dec_to_hex(0x0, 2 * self.__address_length))
        opcodes.add('PUSH', dec_to_hex(0x40 + 0x20, 2 * self.__address_length))
        opcodes.add('MSTORE')

    def store_atom_value(self, opcodes: OpcodeList, atom_address: int):
        """
        INPUT:  | EoS | New value of Atom
        OUTPUT: | EoS |
        """
        self.load_atom_address(opcodes, atom_address)
        opcodes.add('MSTORE')

    def load_atom_address(self, opcodes: OpcodeList, atom_address: int):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of Atom on provided address
        """
        self.load_cur_gap(opcodes)
        opcodes.add('PUSH', dec_to_hex(atom_address, 2 * self.__address_length))
        opcodes.add('ADD')

    def load_atom_value(self, opcodes: OpcodeList, atom_address: int):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Value of Atom on provided address |
        """
        self.load_atom_address(opcodes, atom_address)
        opcodes.add('MLOAD')

    def load_cur_gap(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Gap of current frame |
        """
        opcodes.add('PUSH', dec_to_hex(0, 2 * self.__address_length))
        opcodes.add('MLOAD')

    def store_new_gap(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS | New gap
        OUTPUT: | EoS |
        """
        opcodes.add('PUSH', dec_to_hex(0, 2 * self.__address_length))
        opcodes.add('MSTORE')

    def load_prev_gap(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of previout frame's start
        """
        self.load_cur_gap(opcodes)
        opcodes.add('MLOAD')

    def load_cur_atom_counter_addr(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of Current Atom counter
        """
        self.load_cur_gap(opcodes)
        opcodes.add('PUSH', dec_to_hex(0x20, 2 * self.__address_length))
        opcodes.add('ADD')

    def load_cur_atom_counter(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Value of Current Atom counter
        """
        self.load_cur_atom_counter_addr(opcodes)
        opcodes.add('MLOAD')

    def load_back_address_addr(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Address of Current Back address
        """
        self.load_cur_gap(opcodes)
        opcodes.add('PUSH', dec_to_hex(0x40, 2 * self.__address_length))
        opcodes.add('ADD')

    def load_back_address(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Current Back address
        """
        self.load_back_address_addr(opcodes)
        opcodes.add('MLOAD')

    def store_back_address(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS | New Back address
        OUTPUT: | EoS |
        """
        self.load_back_address_addr(opcodes)
        opcodes.add('MSTORE')

    def calc_cur_frame_size(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Size of current frame
        """
        opcodes.add('PUSH', dec_to_hex(self.__frame_service_atoms * 0x20, 2 * self.__address_length))

        self.load_cur_atom_counter(opcodes)
        opcodes.add('PUSH', dec_to_hex(32, 2 * self.__address_length))
        opcodes.add('MUL')

        opcodes.add('ADD')

    def calc_new_frame_gap(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS | Gap of new frame
        """
        self.load_cur_gap(opcodes)
        self.calc_cur_frame_size(opcodes)
        opcodes.add('ADD')

    def add_frame(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS | Arg1 | ... | ArgN | Back Address |
        OUTPUT: | EoS | Arg1 | ... | ArgN |
        """
        self.load_cur_gap(opcodes)
        self.calc_new_frame_gap(opcodes)
        opcodes.add('MSTORE')

        self.calc_new_frame_gap(opcodes)
        self.store_new_gap(opcodes)

        # Back address gone
        self.store_back_address(opcodes)

    def remove_frame(self, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        self.load_prev_gap(opcodes)

        self.store_new_gap(opcodes)
