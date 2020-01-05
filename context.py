class Context:
    counter: int
    nameByNum: dict
    numByName: dict
    is_prog: bool = False

    def __init__(self, frame_service_atoms: int):
        # ZERO reserved for prev gap
        # ONE reserved for atom countere
        # TWO reserved for back address
        self.counter = frame_service_atoms
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