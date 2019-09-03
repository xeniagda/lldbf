from abc import ABC, abstractmethod

class Context:
    def __init__(self):
        self.variables_with_idxs = []
        self.current_ptr = 0

class BFPPToken(ABC):
    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def into_bf(self, ctx):
        pass

class BFToken(BFPPToken):
    def __init__(self, token):
        super().__init__()
        self.token = token

    def into_bf(self, ctx):
        return self.token

    def __str__(self):
        return self.token

    def __repr__(self):
        return "BFToken('{}')".format(self)

class TokenList(BFPPToken):
    def __init__(self, tokens):
        super().__init__()
        self.tokens = tokens

    def into_bf(self, ctx):
        res = ""
        for x in self.tokens:
            res += x.into_bf(ctx)
        return res

    def __str__(self):
        return "(" + "".join(map(str, self.tokens)) + ")"

    def __repr__(self):
        return "TokenList(" + ",".join(map(repr, self.tokens)) + ")"

class BFLoop(BFPPToken):
    def __init__(self, inner):
        super().__init__()
        self.inner = inner

    def into_bf(self, ctx):
        return "[" + self.inner.into_bf(ctx) + "]"

    def __str__(self):
        return "[" + str(self.inner) + "]"

    def __repr__(self):
        return "Loop(" + repr(self.inner) + ")"



class Repetition(BFPPToken):
    def __init__(self, inner, count):
        super().__init__()
        self.inner = inner
        self.count = count

    def __str__(self, ctx):
        return "(" + str(self.inner) + ") * " + str(self.count)

    def __repr__(self):
        return "Repetition(" + repr(self.inner) + ") * " + repr(self.count)

    def into_bf(self, ctx):
        return self.inner.into_bf(ctx) * self.count


if __name__ == "__main__":
    code = TokenList([
        BFToken("+"),
        BFToken(">"),
        BFToken("+"),
        BFToken("+"),
        BFLoop(BFToken("+")),
        BFToken("+"),
        BFToken("<"),
        BFToken("-"),
        Repetition(BFToken("+"), 10)
    ])

    print(code.into_bf(Centext()))
