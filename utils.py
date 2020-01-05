def dec_to_hex(number: int, pad: int):
    return '0x{0:0{1}X}'.format(number, pad)[2:]
