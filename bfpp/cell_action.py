from abc import ABC, abstractmethod

class CellAction:
    def __init__(self, span):
        self.span = span

    @abstractmethod
    def perform_after(self, before):
        pass

    @abstractmethod
    def repeated(self):
        pass

    @abstractmethod
    def apply_to_value(self, value):
        pass

class Unknown(CellAction):
    def __init__(self, span):
        super(Unknown, self).__init__(span)

    def perform_after(self, before):
        return self

    def repeated(self):
        return self

    def apply_to_value(self, value):
        return None

    def __str__(self):
        return "Unknown"

    __repr__ = __str__

class SetTo(CellAction):
    def __init__(self, span, value):
        super(SetTo, self).__init__(span)
        self.value = value % 256

    def perform_after(self, before):
        return self

    def repeated(self):
        # The count might be zero, therefore we can not be sure
        # (this caused a few bugs where I returned self, before I realized this)
        return Unknown(self.span)

    def apply_to_value(self, value):
        return self.value

    def __str__(self):
        return f'SetTo({self.value})'

    __repr__ = __str__

class Delta(CellAction):
    def __init__(self, span, amount):
        super(Delta, self).__init__(span)
        self.amount = amount % 256

    def perform_after(self, action):
        if isinstance(action, Delta):
            return Delta(None, self.amount + action.amount)

        if isinstance(action, SetTo):
            return SetTo(None, action.value + self.amount)

        return Unknown(None)

    def repeated(self):
        if self.amount == 0:
            return self
        return Unknown(None)

    def apply_to_value(self, value):
        if self.amount == 0:
            return value
        if value is not None:
            return (value + self.amount) % 256
        return None

    def __str__(self):
        return "Delta({})".format(self.amount)

    __repr__ = __str__

if __name__ == "__main__":
    a = SetTo(None, 1)
    b = Delta(None, 5)
    comb = b.perform_after(a)
    print(comb.apply_to_value(5))
