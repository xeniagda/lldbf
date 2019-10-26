class Error:
    def __init__(self, span, msg, note=None):
        self.span = span
        self.msg = msg
        self.note = note

    def show(self):
        print("Error:", self.msg)
        print("\n".join(self.span.show_ascii_art()))
        if self.note is not None:
            print("  note:", self.note)
