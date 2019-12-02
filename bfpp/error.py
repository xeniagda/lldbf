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
        value = self.ctx.known_values[self.ctx.lctx().current_ptr]

        clears = [x for x in value.action_history if isinstance(x, SetTo) and x.span is not None]

        if len(clears) == 0:
            return ["This cell's value has not changed since the beginning of the program"]
        else:
            last_clear = clears[-1]
            span = last_clear.span
            return ["This cell was last cleared from here:", span]

class LoopNotStableError(BaseError):
    def __init__(self, span, ctx):
        super(LoopNotStableError, self).__init__(span)
        self.ctx = ctx

    def msg(self):
        return "Loop marked as stable is not stable!"

    def notes(self):
        last_ctx = self.ctx.lctx_stack[-2]

        if self.ctx.lctx().inv_id != last_ctx.inv_id:
            return ["This loop might contain some unstable element(s)"]
        else:
            starts_at = [
                name
                for name, pos in self.ctx.lctx().named_locations.items()
                if pos == self.ctx.lctx().origin
            ]

            ends_up_at = [
                name
                for name, pos in self.ctx.lctx().named_locations.items()
                if pos == self.ctx.lctx().current_ptr
            ]

            note = "loop ends up at "
            diff = self.ctx.lctx().current_ptr - self.ctx.lctx().origin
            if diff > 0:
                note += "+" + str(diff)
            else:
                note += str(diff)

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
        if len(self.ctx.lctx().named_locations) > 0:
            return ["Defined locations: " + ", ".join(map(f.var, self.ctx.lctx().named_locations.keys()))]
        return []
