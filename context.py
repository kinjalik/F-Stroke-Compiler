class Context:
    id_counter: int
    __name_by_num: dict
    __num_by_name: dict
    is_prog: bool = False

    def __init__(self, frame_service_atoms: int):
        # ZERO reserved for prev gap
        # ONE reserved for atom countere
        # TWO reserved for back address
        self.id_counter = frame_service_atoms
        self.__name_by_num = {}
        self.__num_by_name = {}

    def get_atom_addr(self, name: str):
        is_added = False
        if name not in self.__num_by_name:
            is_added = True
            self.__num_by_name[name] = self.id_counter
            self.__name_by_num[self.id_counter] = name
            self.id_counter += 1
        return self.__num_by_name[name] * 32, is_added