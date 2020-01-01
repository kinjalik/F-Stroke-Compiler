import sys
from enum import Enum
from typing import List
from enum import Enum
from typing import Generic, List, Any


class Terminal(Enum):
    UNKNOWN = -1
    EOF = 1
    SPACE = 2
    LP = 3
    RP = 4
    Letter = 5
    Digit = 6


class Token:
    type: Terminal
    value: str

    def __init__(self, char: str):
        self.value = char
        if char == ' ':
            self.type = Terminal.SPACE
        elif char == '(':
            self.type = Terminal.LP
        elif char == ')':
            self.type = Terminal.RP
        elif char in '1234567890':
            self.type = Terminal.Digit
        elif char in 'qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM':
            self.type = Terminal.Letter
        elif char == chr(0):
            self.type = Terminal.EOF
        else:
            self.type = Terminal.UNKNOWN

    @staticmethod
    def get_eof():
        return Token(chr(0))


class TokenList:
    tokens: List[Token]
    length: int
    currentTokenIndex: int

    def __init__(self, rawCode: str):
        self.tokens = [Token(x) for x in preprocess_code(rawCode)]
        self.tokens.append(Token.get_eof())
        self.length = len(self.tokens)
        self.currentTokenIndex = 0

    def __len__(self):
        return self.length

    def set_current_token_index(self, val: int) -> None:
        self.currentTokenIndex = val

    def get_current_token_index(self) -> int:
        return self.currentTokenIndex

    def get_current_token(self) -> Token:
        return self.tokens[self.currentTokenIndex]

    def get_next_token(self) -> Token:
        return self.tokens[self.currentTokenIndex + 1]

    def inc(self):
        self.currentTokenIndex += 1


def preprocess_code(formatted_code: str):
    formatted_code = formatted_code.replace('\n', ' ')
    formatted_code = formatted_code.replace('\t', ' ')
    while '  ' in formatted_code:
        formatted_code = formatted_code.replace('  ', ' ')
    while formatted_code[-1] == ' ':
        formatted_code = formatted_code[:-1]


    return formatted_code


def get_tokens_array(rawCode: str):
    return [Token(x) for x in preprocess_code(rawCode)]

tokenList: TokenList


class AstNodeType(Enum):
    Program = 0
    List = 1
    Element = 2
    Atom = 3
    Literal = 4
    Identifier = 5
    Integer = 6


class AstNode:
    type: AstNodeType
    value: Any
    child_nodes: List = list()

    def __init__(self, type: AstNodeType, value: Any):
        self.type = type
        self.value = value
        self.child_nodes = list()

    def add_child(self, child_node):
        self.child_nodes.append(child_node)

    @staticmethod
    def process_program():
        global tokenList
        node = AstNode(AstNodeType.Program, None)
        while tokenList.get_current_token().type != Terminal.EOF:
            if tokenList.get_current_token().type == Terminal.SPACE:
                tokenList.inc()
                continue
            node.add_child(AstNode.process_element())
        return node

    @staticmethod
    def process_element():
        global tokenList
        if tokenList.get_current_token().type == Terminal.Letter:
            return AstNode.process_atom()
        elif tokenList.get_current_token().type == Terminal.Digit:
            return AstNode.process_literal()
        elif tokenList.get_current_token().type == Terminal.LP:
            return AstNode.process_list()

    @staticmethod
    def process_list():
        global tokenList
        node = AstNode(AstNodeType.List, None)

        tokenList.inc()
        while tokenList.get_current_token().type != Terminal.RP:
            if tokenList.get_current_token().type == Terminal.SPACE:
                tokenList.inc()
                continue
            node.add_child(AstNode.process_element())
        tokenList.inc()

        return node

    # @staticmethod
    # def process_atom():
    #     global tokenList
    #     logger.debug('Building node: Atom')
    #     node = AstNode(Type.Atom, None)
    #     node.add_child(AstNode.process_identifier())
    #     return node

    @staticmethod
    def process_atom():
        global tokenList
        node = AstNode(AstNodeType.Atom, None)

        value: str = tokenList.get_current_token().value

        tokenList.inc()
        while tokenList.get_current_token().type == Terminal.Letter or tokenList.get_current_token().type == Terminal.Digit:
            value += tokenList.get_current_token().value
            tokenList.inc()

        node.value = value.lower()
        return node

    @staticmethod
    def process_literal():
        global tokenList
        node = AstNode(AstNodeType.Literal, None)
        value = tokenList.get_current_token().value

        tokenList.inc()
        while tokenList.get_current_token().type == Terminal.Digit:
            value += tokenList.get_current_token().value
            tokenList.inc()

        node.value = int(value)
        return node


class AST:
    root: AstNode

    def __init__(self, token_list: TokenList):
        global tokenList
        tokenList = token_list
        tokenList.set_current_token_index(0)
        self.root = AstNode.process_program()


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


    VirtualStackHelper.init_stack(opcodes)

    # Set jump to main program body
    opcodes.add('PUSH', dec_to_hex(0))
    jump_to_prog_start_i = len(opcodes.list) - 1
    opcodes.add('JUMP')

    prog_body = None
    for el in ast.root.child_nodes:
        context = Context()

        if el.child_nodes[0].value == 'prog':
            prog_body = el
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

        else:
            Declared.declare(el, context, opcodes)
    res = opcodes.get_str()
    return res

def validate_byte_code(code: str) -> bool:
    for c in code:
        if c not in '1234567890abcdefABCDEF':
            return False

    insturcion_codes = [getInstructionCode[key] for key in getInstructionCode]

    i = 0
    while i < len(code):
        cur_code = code[i] + code[i + 1]
        i += 2
        if cur_code not in insturcion_codes:
            return False
        if cur_code == getInstructionCode['PUSH']:
            i += 2 * ADDRESS_LENGTH

    return True


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
    if name == 'read':
        return BuiltIns.read(call_body, ctx, opcodes)
    elif name == 'setq':
        return BuiltIns.setq(call_body, ctx, opcodes)
    elif name == 'cond':
        return BuiltIns.cond(call_body, ctx, opcodes)
    elif name == 'while':
        return BuiltIns.wwhile(call_body, ctx, opcodes)
    elif name == 'break':
        return BuiltIns.bbreak(call_body, ctx, opcodes)
    elif name == 'return':
        return BuiltIns.rreturn(call_body, ctx, opcodes)
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
    elif name == 'greatereq':
        return BuiltIns.greatereq(call_body, ctx, opcodes)
    elif name == 'or':
        return BuiltIns.oor(call_body, ctx, opcodes)
    elif name == 'and':
        return BuiltIns.aand(call_body, ctx, opcodes)
    elif name == 'not':
        return BuiltIns.nnot(call_body, ctx, opcodes)

    if name in Declared.addr_by_name:
        return Declared.call(call_body, ctx, opcodes)

    # print(f'No builtin found for {name}')

    return 0
    # print(name)
    # for i in range(1, len(call_body.child_nodes)):
    #     arg = call_body.child_nodes[i]
    #     print(arg.type)


def process_literal(call_body: AstNode, opcodes: OpcodeList):
    assert call_body.type == AstNodeType.Literal
    value = dec_to_hex(call_body.value)
    opcodes.add('PUSH', value)


def process_atom(call_body: AstNode, ctx: Context, opcodes: OpcodeList):
    assert call_body.type == AstNodeType.Atom
    atom_name = call_body.value
    atom_address, is_new = ctx.get_atom_addr(atom_name)
    VirtualStackHelper.load_atom_value(opcodes, atom_address)


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
        opcodes.add('PUSH', dec_to_hex(Declared.addr_by_name[call_body.child_nodes[0].value]))
        opcodes.add('JUMP')

        # Prepare back address, part 2
        opcodes.add('JUMPDEST')
        opcodes.list[back_address].extra_value = dec_to_hex(opcodes.list[-1].id)

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
    def read(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (0): | EoS |
        OUTPUT (1): | EoS | Value from input
        """
        assert len(body.child_nodes) == 2

        process_call(body.child_nodes[1], ctx, opcodes)
        
        opcodes.add('PUSH', dec_to_hex(0x20))
        opcodes.add('MUL')

        opcodes.add('CALLDATALOAD')

    @staticmethod
    def cond(body: AstNode, ctx: Context, opcodes: OpcodeList):
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
        
        assert len(body.child_nodes) == 3
        
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

        assert len(body.child_nodes) == 3
        
        opcodes.add('EQ')

    @staticmethod
    def nonequal(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 differs from Value 2 (bool)
        """
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)

        assert len(body.child_nodes) == 3

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
        assert len(body.child_nodes) == 2
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
        assert len(body.child_nodes) == 3
        opcodes.add('ADD')

    @staticmethod
    def minus(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2 
        OUTPUT (1): | EoS | Value 1 - Value 2
        """
        assert len(body.child_nodes) == 3
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
        assert len(body.child_nodes) == 3
        opcodes.add('MUL')

    @staticmethod
    def divide(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Value 1 // Value 2
        """
        assert len(body.child_nodes) == 3
        opcodes.add('SWAP1')
        opcodes.add('DIV')

    @staticmethod
    def rreturn(body: AstNode, ctx: Context, opcodes: OpcodeList):
        process_call(body.child_nodes[1], ctx, opcodes)
        """
        INPUT  (1): | EoS | Some value 
        OUTPUT (0): | EoS | 
        """
        assert len(body.child_nodes) == 2
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
    current_while = 0

    @staticmethod
    def bbreak(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        assert len(body.child_nodes) == 1
        opcodes.add('PUSH', dec_to_hex(0))
        opcodes.add('JUMP', dec_to_hex(BuiltIns.current_while))
        pass

    @staticmethod
    def wwhile(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT:  | EoS |
        OUTPUT: | EoS |
        """
        assert len(body.child_nodes) == 3
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
        assert len(body.child_nodes) == 3
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
        assert len(body.child_nodes) == 3
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
        assert len(body.child_nodes) == 3
        opcodes.add('LT')


    @staticmethod
    def greatereq(body: AstNode, ctx: Context, opcodes: OpcodeList):
        """
        INPUT  (2): | EoS | Value 1 | Value 2
        OUTPUT (1): | EoS | Does Value 1 less or equals Value (bool)
        """
        assert len(body.child_nodes) == 3
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
        assert len(body.child_nodes) == 3
        opcodes.add('OR')

    @staticmethod
    def aand(body: AstNode, ctx: Context, opcodes: OpcodeList):
        for i in range(1, 3):
            process_call(body.child_nodes[i], ctx, opcodes)
        """
        INPUT  (2): | EoS | v1 (bool) | v2 (bool) 
        OUTPUT (1): | EoS | v1 AND v2 (bool)
        """
        assert len(body.child_nodes) == 3
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


if __name__ == '__main__':
    # code = open('input.fst').read()
    code = sys.stdin.read()
    tokens = TokenList(code)
    tree = AST(tokens)
    print(generate_code(tree))