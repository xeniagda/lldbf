from abc import ABC, abstractmethod
import ascii_tools as f

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
    def notes(self):
        pass

    def show(self):
        print()
        print(f.error(self.name() + ": " + self.msg()))
        print("\n".join(self.span.show_ascii_art()))

        for note in self.notes():
            print(f.note("  note: " + note))

class BaseError(Message):
    def __init__(self, span):
        super(BaseError, self).__init__(span)

    def name(self):
        return "Error"

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
