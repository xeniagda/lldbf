from abc import ABC, abstractmethod
from bfppfile import Span, BFPPFile
from error import *
from context import Context, LocalContext
from cell_action import *

class BFPPToken(ABC):
    @abstractmethod
    def __init__(self, span):
        self.span = span

    @abstractmethod
    def into_bf(self, ctx):
        pass


class Debug(BFPPToken):
    def __init__(self, span):
        super(Debug, self).__init__(span)

    def into_bf(self, ctx):
        print("Debug at")
        print("\n".join(self.span.show_ascii_art()))
        print("Info:")
        print("    ctx =", ctx)

        return ""

    def __str__(self):
        return "debug"

    def __repr__(self):
        return "Debug()"

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

        if self.token == "+":
            ctx.apply_action(Delta(1))
        if self.token == "-":
            ctx.apply_action(Delta(-1))

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
        last_ctx = ctx.lctx()

        if self.is_stable:
            new_lctx = ctx.new_lctx()
        else:
            new_lctx = LocalContext(0, {}, ctx.lctx().inv_id + 1)
        ctx.lctx_stack.append(new_lctx)

        loop_content = self.inner.into_bf(ctx)

        is_stable = ctx.lctx().is_stable_relative_to(last_ctx)
        if is_stable and not self.is_stable:
            # TODO: Give warning
            pass

        if not is_stable and self.is_stable:
            er = LoopNotStableError(
                self.span,
                ctx,
            )
            er.show()
            ctx.n_errors += 1

        ctx.pop_lctx(repeated=True)

        ctx.apply_action(Clear())

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
            er = MemNotFoundError(
                self.span,
                self.location,
                ctx,
            )
            er.show()
            ctx.n_errors += 1
            return ""


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
                msg="`" + str(self.name) + "` is already defined"
            )
            er.show()
            ctx.n_errors += 1

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
                msg="Macro `" + self.name + "` is not defined!",
            )
            er.show()
            ctx.n_errors += 1

            return ""

        fn = ctx.macros[self.name]
        if len(self.args) != len(fn.args.locations):
            er = Error(
                self.span,
                msg="Expected {} variables, got {}".format(len(fn.args.locations), len(self.args)),
            )
            er.show()
            ctx.n_errors += 1

        arg_locs = {}
        # Assign addresses for arguments
        for i in range(len(self.args)):
            var_name = self.args[i]
            arg_name = fn.args.locations[i]

            if var_name not in ctx.lctx().named_locations:
                er = MemNotFoundError(
                    self.span,
                    var_name,
                    ctx,
                )
                er.show()
                ctx.n_errors += 1

                return ""

            arg_locs[arg_name] = ctx.lctx().named_locations[var_name]

        new_lctx = ctx.new_lctx()
        new_lctx.named_locations = arg_locs
        ctx.lctx_stack.append(new_lctx)

        # Go to the active arg in the function
        goto = LocGoto(self.span, fn.args.locations[fn.args.active_idx])
        code = goto.into_bf(ctx)

        # Invoke function
        code += fn.content.into_bf(ctx)

        # Pop the function ctx
        ctx.pop_lctx(repeated=False)

        return code

