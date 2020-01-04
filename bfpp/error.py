from abc import ABC, abstractmethod
import ascii_tools as f
from cell_action import SetTo
from bfppfile import Span

# From https://en.wikibooks.org/wiki/Algorithm_Implementation/Strings/Levenshtein_distance#Python
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    # len(s1) >= len(s2)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1 # j+1 instead of j since previous_row and current_row are one character longer
            deletions = current_row[j] + 1       # than s2
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]

def find_close(target, items, to_str=None):
    if len(items) == 0:
        return items

    items = list(items)

    if to_str == None:
        to_str = lambda x: x

    packed = [
        (x, levenshtein(target, to_str(x)))
        for x in items
    ]
    packed = sorted(packed, key=lambda pack: pack[1])

    best_dist = packed[0][1]
    max_dist = 2 + best_dist * 1.2

    res = [x for x, dist in packed if dist < max_dist]

    return res[:10]


class Message(ABC):
    def __init__(self, span):
        self.span = span

    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def msg(self):
        pass

    @abstractmethod
    def msg_fmt(self, msg):
        pass

    @abstractmethod
    def notes(self):
        pass

    def show(self):
        print()
        print(self.msg_fmt(self.name() + ": " + self.msg()))
        print("\n".join(self.span.show_ascii_art()))

        for note in self.notes():
            if isinstance(note, str):
                print(f.note("  note: " + note))
            if isinstance(note, Span):
                print("\n".join(note.show_ascii_art()))

class BaseError(Message):
    def __init__(self, span):
        super(BaseError, self).__init__(span)

    def name(self):
        return "Error"

    def msg_fmt(self, msg):
        return f.error(msg)

class Warn(Message):
    def __init__(self, span):
        super(BaseError, self).__init__(span)

    def name(self):
        return "Warning"

    def msg_fmt(self, msg):
        return f.warning(msg)

class Error(BaseError):
    def __init__(self, span, msg, note=None):
        self.span = span
        self.message = msg
        self.note = note

    def msg(self):
        return self.message

    def notes(self):
        if self.note is None:
            return []
        return [self.note]

class IneffectiveLoopWarning(Warn):
    def __init__(self, span, ctx):
        self.span = span
        self.ctx = ctx

    def msg(self):
        return "Loop is never executed (cell is garuanteed to be zero)"

    def notes(self):
        # TODO: Maybe show where the Clear came from
        return []

class LoopNotStableError(BaseError):
    def __init__(self, span, ctx, inner_delta):
        super(LoopNotStableError, self).__init__(span)
        self.ctx = ctx
        self.inner_delta = inner_delta

    def msg(self):
        return "Loop marked as stable is not stable!"

    def notes(self):
        if self.inner_delta.ptr_id_delta != 0:
            return ["This loop might contain some unstable element(s)"]
        else:
            starts_at = [
                name
                for name, pos in self.ctx.named_locations.items()
                if pos == self.ctx.ptr
            ]

            ends_up_at = [
                name
                for name, pos in self.ctx.named_locations.items()
                if pos == self.ctx.ptr + self.inner_delta.ptr_delta
            ]

            note = "loop ends up at "
            if self.inner_delta.ptr_delta > 0:
                note += "+" + str(self.inner_delta.ptr_delta)
            else:
                note += str(self.inner_delta.ptr_delta)

            if len(starts_at) > 0 and len(ends_up_at) > 0:
                note_extra = "that is at " + f.var(ends_up_at[0]) + " instead of " + f.var(starts_at[0])
                return [note, note_extra]

            return [note]

class MemNotFoundError(BaseError):
    def __init__(self, span, varname, ctx):
        super(MemNotFoundError, self).__init__(span)
        self.varname = varname
        self.ctx = ctx

    def msg(self):
        return "Could not find memory location " + f.var(self.varname)

    def notes(self):
        closest = find_close(self.varname, self.ctx.named_locations.keys())
        if len(closest) == 1:
            return ["Maybe you meant " + f.var(closest[0]) + "?"]
        if len(closest) > 0:
            return ["Maybe you meant any of: " + ", ".join(map(f.var, closest)) + "?"]
        return []

class MacroNotFoundError(BaseError):
    def __init__(self, span, macname, ctx):
        super(MacroNotFoundError, self).__init__(span)
        self.macname = macname
        self.ctx = ctx

    def msg(self):
        return "Could not find macro " + self.macname

    def notes(self):
        closest = find_close(self.macname, self.ctx.macros.keys())
        if len(closest) == 1:
            return ["Maybe you meant " + closest[0] + "?"]
        if len(closest) > 0:
            return ["Maybe you meant any of: " + ", ".join(closest) + "?"]
        return []

class WrongArgumentCount(BaseError):
    def __init__(self, span, macname, args, ctx):
        super(WrongArgumentCount, self).__init__(span)
        self.macname = macname
        self.args = args
        self.ctx = ctx

    def msg(self):
        return "Wrong number of arguments"

    def notes(self):
        mac = self.ctx.macros[self.macname]
        n_args_wanted = len(mac.args.declarations)
        arg_names = [f.var(x) for x, _ in mac.args.declarations]

        n_args_got = len(self.args)

        return [
            "The function wants {} arguments ({}), you provided {} arguments".format(
                n_args_wanted,
                ", ".join(arg_names),
                n_args_got,
            ),
            "Macro defined here:",
            self.ctx.macros[self.macname].span,
        ]

class WrongArgumentType(BaseError):
    def __init__(self, span, macname, arg_name, got_path, arg_type, got_type, ctx):
        super(WrongArgumentType, self).__init__(span)
        self.macname = macname
        self.arg_name = arg_name
        self.got_path = got_path
        self.arg_type = arg_type
        self.got_type = got_type
        self.ctx = ctx

    def msg(self):
        return "Wrong argument type for argument " + f.var(str(self.got_path))

    def notes(self):
        return [
            "Wanted type {}, got type {}".format(
                self.arg_type, self.got_type
            ),
            "Macro defined here:",
            self.ctx.macros[self.macname].span,
        ]

class DeclareLocnameNotFound(BaseError):
    def __init__(self, span, varname, others):
        super(DeclareLocnameNotFound, self).__init__(span)
        self.varname = varname
        self.others = others

    def msg(self):
        return "Could not find memory location being declared " + f.var(self.varname)

    def notes(self):
        closest = find_close(self.varname, [x for x, _ in self.others])
        if len(closest) == 1:
            return ["Maybe you meant " + closest[0] + "?"]
        if len(closest) > 0:
            return ["Maybe you meant any of: " + ", ".join(closest) + "?"]
        return []


class TypeNotFound(BaseError):
    def __init__(self, span, typename, ctx):
        super(TypeNotFound, self).__init__(span)
        self.typename = typename
        self.ctx = ctx

    def msg(self):
        return "Could not find type " + f.type_(self.typename)

    def notes(self):
        closest = find_close(self.typename, self.ctx.types.keys())
        if len(closest) == 1:
            return ["Maybe you meant " + closest[0] + "?"]
        if len(closest) > 0:
            return ["Maybe you meant any of: " + ", ".join(closest) + "?"]
        return []


class FieldNotFound(BaseError):
    def __init__(self, span, typename, path):
        super(FieldNotFound, self).__init__(span)
        self.typename = typename
        self.path = path

    def msg(self):
        return "Could not find field " + str(self.path) + " in type " + f.type_(self.typename)

    def notes(self):
        # TODO: Find closest and display
        return []

class GotoWide(BaseError):
    def __init__(self, span, type_, ctx):
        super(GotoWide, self).__init__(span)
        self.type_ = type_
        self.ctx = ctx

    def msg(self):
        return f"Cannot go to a wide type {self.type_}."

    def notes(self):
        # TODO
        # Show some fields of size 1
        size = self.ctx.t_get_size(self.type_)
        return [f"The type you're going to has a size of {size} bytes.", "Please go to some field of that type"]
