from abc import ABC, abstractmethod
from add_n_gen import precomp_xyzk_list

MULTILINE_CTX = True
SHOW_CTX_STACK = True
SHOW_MACROS = False
SHOW_KNOWN = True

# TODO: Create some kind of "invalidation id" to keep track of invalidations to the variable
# locations

class LocalContext:
    def __init__(self, named_locations):
        # origin = 0
        self.current_ptr = 0
        self.modified_cells = []

        self.named_locations = named_locations

    def is_stable(self):
        return self.current_ptr == 0

    def copy(self):
        res = LocalContext(self.named_locations.copy())
        res.modified_cells = self.modified_cells

        return res

    def __str__(self):
        return "LocalContext(ptr={},mod={},locs={})".format(
            self.current_ptr,
            self.modified_cells,
            self.named_locations
        )

    def __repr__(self):
        return "LocalContext(ptr={},mod={},locs={})".format(
            self.current_ptr,
            self.modified_cells,
            self.named_locations
        )

class Context:
    def __init__(self):
        self.lctx_stack = [LocalContext({})]

        self.macros = INIT_MACROS.copy()

        self.known_values = {}

    def __str__(self):
        if MULTILINE_CTX:
            fmt = """\
Context(
    {ctx_fmt}={ctx_val},
    {mac_fmt}={mac_val},
    {knw_fmt}={knw_val},
)"""
        else:
            fmt = "Context({ctx_fmt}={ctx_val},{mac_fmt}={mac_val},{knw_fmt}={knw_fmt},)"

        if SHOW_CTX_STACK:
            ctx_fmt = "lctx_stack"
            ctx_val = str(self.lctx_stack)
        else:
            ctx_fmt = "lctx"
            ctx_val = str(self.lctx_stack[-1])

        if SHOW_MACROS:
            mac_fmt = "macros"
            mac_val = str(self.macros)
        else:
            mac_fmt = "#mactros"
            mac_val = len(self.macros)

        if SHOW_KNOWN:
            knw_fmt = "known"
            knw_val = str(self.known_values)
        else:
            knw_fmt = "#known"
            knw_val = len(self.known_values)

        return fmt.format(
            ctx_fmt=ctx_fmt,
            ctx_val=ctx_val,
            mac_fmt=mac_fmt,
            mac_val=mac_val,
            knw_fmt=knw_fmt,
            knw_val=knw_val,
        )

    def lctx(self):
        return self.lctx_stack[-1]

    def new_lctx(self):
        offset = self.lctx().current_ptr
        offset_vals = {
            name: index - offset
            for (name, index) in self.lctx().named_locations.items()
        }
        return LocalContext(offset_vals)

    def copy(self):
        res = Context()
        res.lctx_stack = [lctx.copy() for lctx in self.lctx_stack]
        res.macros = self.macros.copy()
        res.known_values = self.known_values.copy()

        return res

    def pop_lctx(self):
        diff = self.lctx().current_ptr
        self.lctx_stack.pop()
        self.lctx().current_ptr += diff

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
            ctx.lctx().current_ptr += 1
        elif self.token == "<":
            ctx.lctx().current_ptr -= 1

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
        old_ctx = ctx.copy()

        new_lctx = ctx.new_lctx()
        ctx.lctx_stack.append(new_lctx)

        loop_content = self.inner.into_bf(ctx)
        if not ctx.lctx().is_stable():
            # Loop is not stable, remake without any named locations
            new_lctx = LocalContext({})
            old_ctx.lctx_stack.append(new_lctx)

            loop_content = self.inner.into_bf(old_ctx)
            # Hopefully the inner does not mess with the last lctx

        ctx.pop_lctx()
        return "[" + loop_content + "]"

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
            ctx.lctx().named_locations[name] = ctx.lctx().current_ptr + delta_ptr

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
        if self.location in ctx.lctx().named_locations:
            mem_idx = ctx.lctx().named_locations[self.location]
            delta = mem_idx - ctx.lctx().current_ptr
            ctx.lctx().current_ptr = mem_idx
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

        arg_locs = {}
        # Assign addresses for arguments
        for i in range(len(self.args)):
            var_name = self.args[i]
            arg_name = fn.args.locations[i]
            arg_locs[arg_name] = ctx.lctx().named_locations[var_name] - ctx.lctx().current_ptr

        new_lctx = LocalContext(arg_locs)
        ctx.lctx_stack.append(new_lctx)

        # Go to the active arg in the function
        goto = LocGoto(fn.args.locations[fn.args.active_idx])
        code = goto.into_bf(ctx)

        # Invoke function
        code += fn.content.into_bf(ctx)

        # Pop the function ctx
        ctx.pop_lctx()

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
