import copy
from collections import defaultdict
from abc import ABC, abstractmethod
from bfppfile import Span, BFPPFile
from error import *
from context import State, StateDelta
from cell_action import *
import bfpp_types

class BFPPToken(ABC):
    @abstractmethod
    def __init__(self, span):
        self.span = span

    @abstractmethod
    def into_bf(self, ctx):
        pass

    @abstractmethod
    def get_delta(self, ctx):
        pass

class Debug(BFPPToken):
    def __init__(self, span):
        super(Debug, self).__init__(span)

    def into_bf(self, ctx):
        print("Debug at")
        print("\n".join(self.span.show_ascii_art()))
        print("Info:")
        print("    ctx =", ctx)
        print()

        return ""

    def get_delta(self, ctx):
        return StateDelta()

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
        return self.token

    def get_delta(self, ctx):
        if self.token == ">":
            return StateDelta(1)

        elif self.token == "<":
            return StateDelta(-1)

        if self.token == "+":
            return StateDelta.do_action(Delta(self.span, 1))

        if self.token == "-":
            return StateDelta.do_action(Delta(self.span, -1))

        if self.token == ",":
            return StateDelta.do_action(Unknown(self.span))

        return StateDelta(0)

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
            delta = x.get_delta(ctx.silent())
            ctx.apply_delta(delta)

        return res

    def get_delta(self, ctx):
        total_delta = StateDelta()
        for x in self.tokens:
            delta = x.get_delta(ctx)
            ctx = ctx.with_delta_applied(delta)
            total_delta = total_delta @ delta

        return total_delta

    def __str__(self):
        return "(" + ";".join(map(str, self.tokens)) + ")"

    def __repr__(self):
        return "TokenList(" + ",".join(map(repr, self.tokens)) + ")"


class BFLoop(BFPPToken):
    def __init__(self, span, is_stable, inner):
        super().__init__(span)
        self.inner = inner
        self.is_stable = is_stable

    def into_bf(self, ctx):
        is_effective = ctx.cell_values[ctx.ptr] != 0

        if not ctx.quiet and not is_effective:
            warn = IneffectiveLoopWarning(self.span, ctx)
            warn.show()

        # When generating the inner code, we want to generate code assuming the loop has already run
        # an indeterminate number of times.
        # Eg. if inner loops over some value which is currently zero, and then modifies the value
        # afterwards, we don't want to optimize the loop

        preloop = self.get_inner_delta_rep(ctx)

        ctx.apply_delta(preloop)

        code = "[" + self.inner.into_bf(ctx) + "]"
        if is_effective:
            return code
        else:
            # Maybe evaluate inner.into_bf(ctx) to check for warnings?
            return ""

    def get_inner_delta_rep(self, ctx):
        inner_delta = self.inner.get_delta(ctx)

        if not ctx.quiet and self.is_stable and not inner_delta.is_stable():
            er = LoopNotStableError(
                self.span,
                ctx,
                inner_delta,
            )
            er.show()
            ctx.n_errors += 1

            # Assume the intention was to write a stable loop
            inner_delta.ptr_delta = 0
            inner_delta.ptr_id_delta = 0

        if not self.is_stable:
            inner_delta.ptr_delta = 0
            inner_delta.ptr_id_delta += 1

        # Maybe warn on unneeded unstable loop

        return inner_delta.repeated()

    def get_delta(self, ctx):
        res = self.get_inner_delta_rep(ctx)
        reset_current = StateDelta.do_action(SetTo(self.span, 0))

        return res @ reset_current

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
            ctx.apply_delta(self.inner.get_delta(ctx.silent()))

        return res

    def get_delta(self, ctx):
        total = StateDelta()
        for i in range(self.count):
            total @= self.inner.get_delta(ctx)
            ctx.apply_delta(self.inner.get_delta(ctx))
        return total

class LocDec(BFPPToken):
    def __init__(self,  span, bare):
        super().__init__(span)
        self.bare = bare

    def __repr__(self):
        return "LocDec(" + repr(self.bare) + ")"

    def __str__(self):
        return "declare " + str(self.bare)

    def into_bf(self, ctx):
        self.get_delta(ctx)
        return ""

    def get_delta(self, ctx):
        for name, (idx, type_name) in self.bare.get_var_offsets_and_type_names(ctx).items():
            ctx.named_locations[name] = idx
            ctx.name_type_names[name] = type_name

        return StateDelta()


class LocGoto(BFPPToken):
    def __init__(self, span, path):
        super().__init__(span)
        self.path = path

    def __str__(self):
        return "to " + str(self.path)

    def __repr__(self):
        return "LocGoto(" + repr(self.path) + ")"

    def into_bf(self, ctx):
        delta = self.get_delta(ctx)

        if delta.ptr_delta > 0:
            return ">" * delta.ptr_delta
        else:
            return "<" * (-delta.ptr_delta)

    def get_delta(self, ctx):
        at, type_ = self.path.get_location_and_type(ctx)

        if ctx.t_get_size(type_) != 1:
            if not ctx.quiet:
                err = GotoWide(self.span, type_, ctx)
                err.show()
                ctx.n_errors += 1

        delta = at - ctx.ptr
        return StateDelta(delta)

class Undeclare(BFPPToken):
    def __init__(self, span, unvars):
        super().__init__(span)
        self.unvars = unvars

    def __str__(self):
        return "undeclare (" + ",".join(str(self.unvars)) + ")"

    def __repr__(self):
        return "Undeclare(" + repr(self.unvars) + ")"

    def into_bf(self, ctx):
        self.get_delta(ctx)
        return ""

    def get_delta(self, ctx):
        for unvar in self.unvars:
            if unvar in ctx.named_locations and unvar in ctx.name_type_names:
                del ctx.named_locations[unvar]
                del ctx.name_type_names[unvar]
            else:
                if not ctx.quiet:
                    er = MemNotFoundError(
                        self.span,
                        str(self),
                        ctx,
                    )
                    er.show()
                    ctx.n_errors += 1

        return StateDelta()

class AssumeStable(BFPPToken):
    def __init__(self, span, content):
        super().__init__(span)
        self.content = content

    def __str__(self):
        return "assume stable {" + str( self.content) + "}"

    def __repr__(self):
        return "AssumeStable(content=" + repr(self.content) + ")"

    def into_bf(self, ctx):
        inner_code = self.content.into_bf(ctx)
        # For safety, assume all cells were modified
        ctx.cell_values = defaultdict(lambda: None)
        return inner_code

    def get_delta(self, ctx):
        inner_delta = self.content.get_delta(ctx)
        inner_delta.ptr_delta = 0
        inner_delta.ptr_id_delta = 0

        return inner_delta

class DeclareMacro(BFPPToken):
    def __init__(self, span, name, args, content):
        super().__init__(span)
        self.name = name
        self.args = args
        self.content = content

    def __str__(self):
        return "def " + self.name + str(self.args) + "{" + str(
            self.content) + "}"

    def __repr__(self):
        return "Define(" + self.name + "," + repr(
            self.args) + "," + repr(self.content) + ")"

    def into_bf(self, ctx):
        if not ctx.quiet and self.name in ctx.macros.keys():
            er = Error(
                self.span,
                msg="macro " + str(self.name) + " is already defined"
            )
            er.show()
            ctx.n_errors += 1
            return ""

        # Dry-run macro to check for errors/warnings
        dry_ctx = State()
        dry_ctx.macros = ctx.macros
        dry_ctx.types = ctx.types
        # Make sure all values are unknown
        dry_ctx.cell_values = defaultdict(lambda: None)
        dry_ctx.quiet = ctx.quiet

        # Fill in args
        for arg, (at, type_name) in self.args.get_var_offsets_and_type_names(dry_ctx).items():
            dry_ctx.named_locations[arg] = at
            dry_ctx.name_type_names[arg] = type_name

        _ = self.content.into_bf(dry_ctx)

        ctx.macros[self.name] = self
        return ""

    def get_delta(self, ctx):
        return StateDelta()

class InvokeMacro(BFPPToken):
    def __init__(self, span, name, args):
        super().__init__(span)
        self.name = name
        self.args = args

    def __str__(self):
        return "invoke " + self.name + str(self.args)

    def __repr__(self):
        return "Invoke(" + self.name + "," + str(self.args) + ")"

    def get_code_and_subctx(self, ctx):
        if self.name not in ctx.macros.keys():
            if not ctx.quiet:
                er = MacroNotFoundError(
                    self.span,
                    self.name,
                    ctx,
                )
                er.show()
                ctx.n_errors += 1

            return TokenList(self.span, []), State()

        fn = ctx.macros[self.name]

        sub_ctx = State()
        sub_ctx.macros = ctx.macros
        sub_ctx.types = ctx.types
        sub_ctx.ptr = ctx.ptr
        sub_ctx.cell_values = ctx.cell_values
        sub_ctx.quiet = True

        # Fill in arguments and types

        if len(self.args) != len(fn.args.declarations):
            er = WrongArgumentCount(
                self.span,
                self.name,
                self.args,
                ctx,
            )
            er.show()
            ctx.n_errors += 1

        invalid_types = False
        for arg, (name, (offset, type_name)) in zip(self.args, fn.args.get_var_offsets_and_type_names(sub_ctx).items()):
            location, current_type_name = arg.get_location_and_type(ctx)

            if current_type_name != type_name:
                invalid_types = True

                if not ctx.quiet:
                    er = WrongArgumentType(
                        self.span,
                        self.name,
                        name,
                        arg,
                        type_name,
                        current_type_name,
                        ctx,
                    )
                    er.show()
                    ctx.n_errors += 1

            sub_ctx.named_locations[name] = location
            sub_ctx.name_type_names[name] = type_name

        goto = LocGoto(self.span, fn.args.relative[1])
        fn_with_goto = TokenList(self.span, [goto, fn.content])

        return fn_with_goto, sub_ctx

    def into_bf(self, ctx):
        f, sub_ctx = self.get_code_and_subctx(ctx)

        return f.into_bf(sub_ctx)

    def get_delta(self, ctx):
        f, sub_ctx = self.get_code_and_subctx(ctx)

        return f.get_delta(sub_ctx)

class TypeDec(BFPPToken):
    def __init__(self, span, typename, fields):
        super().__init__(span)

        self.typename = typename
        self.fields = fields

    def __str__(self):
        return "struct " + self.typename + "{" + ",".join(f + ": " + str(ty) for f, ty in self.fields) + "}"

    def __repr__(self):
        return "TypeDec(typename={}, fields={})".format(self.typename, self.fields)

    def into_bf(self, ctx):
        if self.typename in ctx.types.keys():
            # Error?
            pass

        type_ = bfpp_types.Struct(self.fields)
        ctx.types[self.typename] = type_

        return ""

    def get_delta(self, ctx):
        return StateDelta()

class Path:
    def __init__(self, span, parts):
        self.span = span
        self.parts = parts

    def __repr__(self):
        return "Path(" + ".".join(self.parts) + ")"

    def __str__(self):
        return ".".join(self.parts)

    def get_location_and_type(self, ctx):
        name = self.parts[0]
        if name not in ctx.named_locations:
            if not ctx.quiet:
                er = MemNotFoundError(
                    self.span,
                    str(self),
                    ctx,
                )
                er.show()
                ctx.n_errors += 1
            return 0, "Byte"

        var_offset = ctx.named_locations[name]

        var_type_name = ctx.name_type_names[name]

        offset_and_type = ctx.t_get_offset_and_type_for_path(var_type_name, self.parts[1:])
        if offset_and_type == None:
            if not ctx.quiet:
                er = FieldNotFound(
                    self.span,
                    ctx.name_type_names[name],
                    self
                )
                er.show()
                ctx.n_errors += 1
            return 0, "Byte"

        offset, type_ = offset_and_type

        return var_offset + offset, type_

class LocDecBare:
    def __init__(self, span, declarations, relative):
        self.span = span

        self.declarations = declarations # List of tuples, [(name, type)]
        self.relative = relative

    def get_var_offsets_and_type_names(self, ctx):
        if self.relative[0] == None:
            rel_from_ptr = ctx.ptr
        else:
            loc, type_ = self.relative[0].get_location_and_type(ctx)
            if ctx.t_get_size(type_) != 1:
                if not ctx.quiet:
                    err = GotoWide(self.span, type_, ctx)
                    err.show()
                    ctx.n_errors += 1

            rel_from_ptr = loc

        active_relative_ptr = None

        at = 0
        result_relative = {}
        for name, type_name in self.declarations:
            if type_name not in ctx.types.keys():
                if not ctx.quiet:
                    er = TypeNotFound(
                        self.span,
                        type_name,
                        ctx
                    )
                    er.show()
                    ctx.n_errors += 1

                # We don't want to display a "Could not find memory location being declared..." error here
                # So we do a special case
                if name == self.relative[1].parts[0]:
                    active_relative_ptr = at
                continue

            result_relative[name] = (at, type_name)

            if self.relative[1].parts[0] == name:
                offset_and_type = ctx.t_get_offset_and_type_for_path(type_name, self.relative[1].parts[1:])
                if offset_and_type != None:
                    offset, type_ = offset_and_type
                    if ctx.t_get_size(type_) != 1:
                        if not ctx.quiet:
                            err = GotoWide(self.span, type_, ctx)
                            err.show()
                            ctx.n_errors += 1

                    active_relative_ptr = at + offset

            at += ctx.t_get_size(type_name)

        if active_relative_ptr is None:
            if not ctx.quiet:
                er = DeclareLocnameNotFound(
                    self.span,
                    str(self.relative[1]),
                    self.declarations,
                )
                er.show()
                ctx.n_errors += 1

            active_relative_ptr = 0

        return {name: (i - active_relative_ptr + ctx.ptr + rel_from_ptr, type_name) for name, (i, type_name) in result_relative.items()}

    def __repr__(self):
        return "LocDecBare([" + ",".join("(" + name + "," + repr(type_) + ")" for name, type_ in self.declarations) + "]," + repr(self.active_path) + ")"

    def __str__(self):
        return "(" + ", ".join(name + ": " + str(type_) for name, type_ in self.declarations) + ") at " + str(self.active_path)

