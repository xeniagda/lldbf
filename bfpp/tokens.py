from abc import ABC, abstractmethod
from add_n_gen import precomp_xyzk_list


class Context:
    def __init__(self):
        self.lwi_list = [{}]
        self.org_id = 0
        self.offset = 0

        self.macros = INIT_MACROS.copy()

    def __str__(self):
        return "Context(loc=#{}+{}, lwi={})".format(self.org_id, self.offset,
                                                    self.locations_with_idxs())

    def locations_with_idxs(self):
        return self.lwi_list[self.org_id]

    def reorigin_empty(self):
        self.org_id = len(self.lwi_list)
        self.offset = 0
        self.lwi_list.append({})

    def reorigin_copy(self):
        last_lwi = self.lwi_list[self.org_id]

        self.org_id = len(self.lwi_list)

        self.lwi_list.append(
            {loc: last_lwi[loc] - self.offset
             for loc in last_lwi.keys()})

        self.offset = 0


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
        if self.token == ">":
            ctx.offset += 1
        elif self.token == "<":
            ctx.offset -= 1

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
        last_id = ctx.org_id
        last_offset = ctx.offset

        ctx.reorigin_copy()

        new_id = ctx.org_id

        inner_bf = self.inner.into_bf(ctx)
        if ctx.org_id == new_id and ctx.offset == 0:
            # The loop is stable, go back to old state
            ctx.org_id = last_id
            ctx.offset = last_offset
        else:
            # The loop moved, making it unstable. The loop might have depended on some now unstable
            # memory location, which makes inner_bf invalid. We will remake it
            ctx.reorigin_empty()
            inner_bf = self.inner.into_bf(ctx)

        return "[" + inner_bf + "]"

    def __str__(self):
        return "[" + str(self.inner) + "]"

    def __repr__(self):
        return "Loop(" + repr(self.inner) + ")"


class Repetition(BFPPToken):
    def __init__(self, inner, count):
        super().__init__()
        self.inner = inner
        self.count = count

    def __str__(self):
        return "(" + str(self.inner) + ") * " + str(self.count)

    def __repr__(self):
        return "Repetition(" + repr(self.inner) + ") * " + repr(self.count)

    def into_bf(self, ctx):
        res = ""
        for i in range(self.count):
            res += self.inner.into_bf(ctx)
        return res


class LocDec(BFPPToken):
    def __init__(self, locations, active_idx):
        super().__init__()
        self.locations = locations
        self.active_idx = active_idx

    def __str__(self):
        return \
            "(?" + \
            " ".join(
                (">" if i == self.active_idx else "") + x for i, x in enumerate(self.locations)
            ) + ")"

    def __repr__(self):
        return \
            "LocDec(" + \
            " ".join(
                (">" if i == self.active_idx else "") + x for i, x in enumerate(self.locations)
            ) + ")"

    def into_bf(self, ctx):
        for i, name in enumerate(self.locations):
            delta_ptr = i - self.active_idx
            ctx.locations_with_idxs()[name] = ctx.offset + delta_ptr

        return ""


class LocGoto(BFPPToken):
    def __init__(self, loc):
        super().__init__()
        self.location = loc

    def __str__(self):
        return "(!" + self.location + ")"

    def __repr__(self):
        return "LocGoto(" + self.location + ")"

    def into_bf(self, ctx):
        if self.location in ctx.locations_with_idxs():
            mem_idx = ctx.locations_with_idxs()[self.location]
            delta = mem_idx - ctx.offset
            ctx.offset = mem_idx
            if delta > 0:
                return ">" * delta
            else:
                return "<" * (-delta)
        else:
            raise RuntimeError("Memory location " + self.location +
                               " not found!")


class DeclareMacro(BFPPToken):
    def __init__(self, name, args, content):
        super().__init__()
        self.name = name
        self.args = args
        self.content = content

    def __str__(self):
        return "define " + self.name + str(self.args) + "{" + str(
            self.content) + "}"

    def __repr__(self):
        return "Define(name=" + self.name + ",args=" + repr(
            self.args) + ",content=" + repr(self.content) + ")"

    def into_bf(self, ctx):
        if self.name in ctx.macros.keys():
            raise ValueError(
                str(self.name) + " is already defined as " +
                str(ctx.macros[self.name]))

        ctx.macros[self.name] = self
        return ""


class InvokeMacro(BFPPToken):
    def __init__(self, name, args):
        super().__init__()
        self.name = name
        self.args = args

    def __str__(self):
        return "invoke " + self.name + "(" + ",".join(self.args) + ")"

    def __repr__(self):
        return "Invoke(name=" + self.name + ",args=(" + ",".join(
            self.args) + ")"

    def into_bf(self, ctx):
        if self.name not in ctx.macros.keys():
            raise ValueError(self.name + " is not defined!")

        fn = ctx.macros[self.name]
        if len(self.args) != len(fn.args.locations):
            raise ValueError("Wrong number of arguments in call to " +
                             self.name + "!")

        old_org = ctx.org_id
        old_offset = ctx.offset
        old_lwi = ctx.locations_with_idxs()

        ctx.reorigin_empty()
        new_id = ctx.org_id
        ctx.offset = old_offset

        # Assign addresses for arguments
        for i in range(len(self.args)):
            var_name = self.args[i]
            arg_name = fn.args.locations[i]
            ctx.locations_with_idxs()[arg_name] = old_lwi[var_name]

        # Go to the active arg in the function
        goto = LocGoto(fn.args.locations[fn.args.active_idx])
        code = goto.into_bf(ctx)

        # Invoke function
        code += fn.content.into_bf(ctx)

        if ctx.org_id == new_id:
            ctx.org_id = old_org
        else:
            ctx.reorigin_empty()

        return code


def inc_by(n):
    n = n % 256
    if n == 0:
        return TokenList([])
    if n < 128:
        return Repetition(BFToken("+"), n)
    else:
        return Repetition(BFToken("-"), 256 - n)


INIT_MACROS = {}

# Generate setN
for i in range(256):
    (x, y, z, k) = precomp_xyzk_list[i]

    if y == z:
        fn_body = TokenList([
            LocGoto("res"),
            inc_by(k + x),
        ])
    elif y == 0:
        fn_body = TokenList([
            LocGoto("res"),
            inc_by(k),
        ])
    else:
        fn_body = TokenList([
            LocGoto("tmp"),
            inc_by(x),
            BFLoop(
                TokenList([
                    LocGoto("res"),
                    inc_by(y),
                    LocGoto("tmp"),
                    inc_by(-z),
                ])),
            LocGoto("res"),
            inc_by(k),
        ])

    args = LocDec(["res", "tmp"], 1)

    fn = DeclareMacro("add" + str(i), args, fn_body)
    INIT_MACROS["add" + str(i)] = fn

    dec_n = 256 - i
    if i == 0:
        dec_n = 0
    fn = DeclareMacro("dec" + str(dec_n), args, fn_body)
    INIT_MACROS["dec" + str(dec_n)] = fn

if __name__ == "__main__":
    ctx = Context()
    dec = LocDec(["a", "b", "c"], 1)
    goto = LocGoto("c")

    code = TokenList([dec, goto]).into_bf(ctx)
    print(code, ctx)
