from abc import ABC, abstractmethod

class Type(ABC):
    @abstractmethod
    def __str__(self):
        pass

    def __repr__(self):
        return str(self)

    @abstractmethod
    def get_fields(self):
        pass

    @abstractmethod
    def get_native_size(self):
        pass

class Byte(Type):
    def __init__(self):
        super(Byte, self).__init__()

    def get_fields(self):
        return []

    def __str__(self):
        return "Byte"

    def get_native_size(self):
        return 1


class Struct(Type):
    def __init__(self, fields):
        super(Struct, self).__init__()
        self.fields = fields

    def get_native_size(self):
        return 0

    def get_fields(self):
        return self.fields

    def __str__(self):
        return "Struct { " + ", ".join(field_name + ": " + str(field_type) for field_name, field_type in self.fields) + " }"

if __name__ == "__main__":
    from context import State

    state = State()
    state.types["Byte"] = Byte()
    state.types["Content"] = Struct([("a", "Byte"), ("b", "Byte")])
    state.types["X"] = Struct(
        [
            ("content", "Content"),
            ("is_present", "Byte")
        ]
    )

    print(state.t_get_offset_and_type_for_path("X", ["content"]))
    print(state.t_get_size("X"))
