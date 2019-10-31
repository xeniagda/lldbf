from abc import ABC, abstractmethod
from add_n_gen import precomp_xyzk_list
from bfppfile import Span, BFPPFile
from error import Error

MULTILINE_CTX = True
SHOW_CTX_STACK = True
SHOW_MACROS = False
SHOW_KNOWN = True

class LocalContext:
    def __init__(self, named_locations, inv_id):
        self.inv_id = inv_id
        self.current_ptr = 0
        self.modified_cells = []

        self.named_locations = named_locations

    def is_stable_relative_to(self, other):
        return self.current_ptr == 0 and self.inv_id == other.inv_id

    def copy(self):
        res = LocalContext(self.named_locations.copy(), self.inv_id)
        res.modified_cells = self.modified_cells

        return res

    def __str__(self):
        return "LocalContext(ptr={},mod={},locs={},inv_id={})".format(
            self.current_ptr,
            self.modified_cells,
            self.named_locations,
            self.inv_id,
        )

    def __repr__(self):
        return "LocalContext(ptr={},mod={},locs={},inv_id={})".format(
            self.current_ptr,
            self.modified_cells,
            self.named_locations,
            self.inv_id,
        )

class Context:
    def __init__(self):
        self.lctx_stack = [LocalContext({}, 0)]

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
        return LocalContext(offset_vals, self.lctx().inv_id)

    def copy(self):
        res = Context()
        res.lctx_stack = [lctx.copy() for lctx in self.lctx_stack]
        res.macros = self.macros.copy()
        res.known_values = self.known_values.copy()

        return res

    def pop_lctx(self):
        diff = self.lctx().current_ptr
        inv_id = self.lctx().inv_id

        self.lctx_stack.pop()

        if inv_id != self.lctx().inv_id:
            self.lctx().named_locations = {}

        self.lctx().current_ptr += diff

class BFPPToken(ABC):
    @abstractmethod
    def __init__(self, span):
        self.span = span

    @abstractmethod
    def into_bf(self, ctx):
        pass


class BFToken(BFPPToken):
    def __init__(self, span, token):
        super().__init__(span)
        assert token in "+-.,<>"

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
    def __init__(self, span, tokens):
        super().__init__(span)
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
    def __init__(self, span, is_stable, inner):
        super().__init__(span)
        self.inner = inner
        self.is_stable = is_stable

    def into_bf(self, ctx):
        # new_lctx = ctx.new_lctx()
        # ctx.lctx_stack.append(new_lctx)

        # loop_content = self.inner.into_bf(ctx)
        # if not ctx.lctx().is_stable():
        #     ctx.pop_lctx()

        #     # Loop is not stable, remake without any named locations
        #     new_lctx = LocalContext({}, ctx.lctx().inv_id + 1)
        #     ctx.lctx_stack.append(new_lctx)

        #     loop_content = self.inner.into_bf(ctx)
        #     # Hopefully the inner does not mess with the last lctx

        # ctx.pop_lctx()
        # return "[" + loop_content + "]"

        last_ctx = ctx.lctx()

        if self.is_stable:
            new_lctx = ctx.new_lctx()
        else:
            new_lctx = LocalContext({}, ctx.lctx().inv_id + 1)
        ctx.lctx_stack.append(new_lctx)

        loop_content = self.inner.into_bf(ctx)

        is_stable = ctx.lctx().is_stable_relative_to(last_ctx)
        if is_stable and not self.is_stable:
            # TODO: Give warning
            pass

        if not is_stable and self.is_stable:
            if ctx.lctx().inv_id != last_ctx.inv_id:
                note = "This loop might contain some unstable element(s)"
            else:
                note = "This loop ends up at "
                if ctx.lctx().current_ptr < 0:
                    note += "+" + str(ctx.lctx().current_ptr)
                else:
                    note += str(ctx.lctx().current_ptr)

            er = Error(
                self.span,
                msg="Loop marked as stable is not stable!",
                note=note,
            )
            er.show()
            exit()

        ctx.pop_lctx()

        return "[" + loop_content + "]"

    def __str__(self):
        return "[" + str(self.inner) + "]"

    def __repr__(self):
        return "Loop(stable=" + str(self.is_stable) + "inner=" + repr(self.inner) + ")"


class Repetition(BFPPToken):
    def __init__(self, span, inner, count):
        super().__init__(span)
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
    def __init__(self,  span, locations, active_idx):
        super().__init__(span)
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
    def __init__(self, span, loc):
        super().__init__(span)
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
            er = Error(
                self.span,
                msg="Memory location " + self.location + " not found!",
                note="Defined locations: " + ", ".join(ctx.lctx().named_locations.keys())
            )
            er.show()
            exit()


class DeclareMacro(BFPPToken):
    def __init__(self, span, name, args, content):
        super().__init__(span)
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
            er = Error(
                self.span,
                msg=str(self.name) + " is already defined as " + str(ctx.macros[self.name]),
            )
            er.show()
            exit()

        ctx.macros[self.name] = self
        return ""


class InvokeMacro(BFPPToken):
    def __init__(self, span, name, args):
        super().__init__(span)
        self.name = name
        self.args = args

    def __str__(self):
        return "invoke " + self.name + "(" + ",".join(self.args) + ")"

    def __repr__(self):
        return "Invoke(name=" + self.name + ",args=(" + ",".join(
            self.args) + ")"

    def into_bf(self, ctx):
        if self.name not in ctx.macros.keys():
            # TODO: Search for macros with similar names?
            er = Error(
                self.span,
                msg="Macro " + self.name + " is not defined!",
            )
            er.show()
            exit()

        fn = ctx.macros[self.name]
        if len(self.args) != len(fn.args.locations):
            er = Error(
                self.span,
                msg="Expected {} variables, got {}".format(len(fn.args.locations), len(self.args)),
            )
            er.show()
            exit()

        arg_locs = {}
        # Assign addresses for arguments
        for i in range(len(self.args)):
            var_name = self.args[i]
            arg_name = fn.args.locations[i]

            if var_name not in ctx.lctx().named_locations:
                er = Error(
                    self.span,
                    msg="Memory location " + var_name + " not found!",
                    note="Defined locations: " + ", ".join(ctx.lctx().named_locations.keys())
                )
                er.show()
                exit()

            arg_locs[arg_name] = ctx.lctx().named_locations[var_name] - ctx.lctx().current_ptr

        new_lctx = LocalContext(arg_locs, ctx.lctx().inv_id)
        ctx.lctx_stack.append(new_lctx)

        # Go to the active arg in the function
        goto = LocGoto(self.span, fn.args.locations[fn.args.active_idx])
        code = goto.into_bf(ctx)

        # Invoke function
        code += fn.content.into_bf(ctx)

        # Pop the function ctx
        ctx.pop_lctx()

        return code

PREGEN_SPAN = Span(BFPPFile("PREGENERATED", ""), 0, 0)

def inc_by(n):
    n = n % 256
    if n == 0:
        return TokenList(PREGEN_SPAN, [])
    if n < 128:
        return Repetition(None, BFToken(PREGEN_SPAN, "+"), n)
    else:
        return Repetition(None, BFToken(PREGEN_SPAN, "-"), 256 - n)


INIT_MACROS = {}

# Generate setN
for i in range(256):
    (x, y, z, k) = precomp_xyzk_list[i]

    if y == z:
        fn_body = TokenList(PREGEN_SPAN, [
            LocGoto(PREGEN_SPAN, "res"),
            inc_by(k + x),
        ])
    elif y == 0:
        fn_body = TokenList(PREGEN_SPAN, [
            LocGoto(PREGEN_SPAN, "res"),
            inc_by(k),
        ])
    else:
        fn_body = TokenList(PREGEN_SPAN, [
            LocGoto(PREGEN_SPAN, "tmp"),
            inc_by(x),
            BFLoop(
                None,
                True,
                TokenList(PREGEN_SPAN, [
                    LocGoto(PREGEN_SPAN, "res"),
                    inc_by(y),
                    LocGoto(PREGEN_SPAN, "tmp"),
                    inc_by(-z),
                ])),
            LocGoto(PREGEN_SPAN, "res"),
            inc_by(k),
        ])

    args = LocDec(PREGEN_SPAN, ["res", "tmp"], 1)

    fn = DeclareMacro(PREGEN_SPAN, "add" + str(i), args, fn_body)
    INIT_MACROS["add" + str(i)] = fn

    dec_n = 256 - i
    if i == 0:
        dec_n = 0
    fn = DeclareMacro(PREGEN_SPAN, "dec" + str(dec_n), args, fn_body)
    INIT_MACROS["dec" + str(dec_n)] = fn

if __name__ == "__main__":
    ctx = Context()
    dec = LocDec(PREGEN_SPAN, ["a", "b", "c"], 1)
    goto = LocGoto(PREGEN_SPAN, "c")

    code = TokenList(PREGEN_SPAN, [dec, goto]).into_bf(ctx)
    print(code, ctx)
