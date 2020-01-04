from abc import ABC, abstractmethod
import ascii_tools as f
from cell_action import SetTo
from bfppfile import Span

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
        if len(self.ctx.named_locations) > 0:
            return ["Defined locations: " + ", ".join(map(f.var, self.ctx.named_locations.keys()))]
        return []

class DeclareLocnameNotFound(BaseError):
    def __init__(self, span, varname, others):
        super(DeclareLocnameNotFound, self).__init__(span)
        self.varname = varname
        self.others = others

    def msg(self):
        return "Could not find memory location " + f.var(self.varname)

    def notes(self):
        # TODO: Find closest and display
        return []

class TypeNotFound(BaseError):
    def __init__(self, span, typename):
        super(TypeNotFound, self).__init__(span)
        self.typename = typename

    def msg(self):
        return "Could not find type " + f.type_(self.typename)

    def notes(self):
        # TODO: Find closest and display
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
