from abc import ABC, abstractmethod

# Brainfuck preprocessor

# Things:
#   * Comments using hash
#   * Address labels
#   * Define blocks
#   * Command repetition
#   * Value generation
# * = TODO

class BFPPToken(ABC):
    @abstractmethod
    def __init__(self):
        pass

class BFToken(BFPPToken):
    def __init__(self, token):
        super().__init__()
        self.token = token

    def __str__(self):
        return self.token

    def __repr__(self):
        return "BFToken('{}')".format(self)

class Repetition(
