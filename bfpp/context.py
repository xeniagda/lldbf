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

        self.macros = {}

        self.known_values = {}

        self.n_errors = 0

    def __str__(self):
        if MULTILINE_CTX:
            fmt = """\
Context(
    {ctx_fmt}={ctx_val},
    {mac_fmt}={mac_val},
    {knw_fmt}={knw_val},
    n_errors={n_errors},
)"""
        else:
            fmt = "Context({ctx_fmt}={ctx_val},{mac_fmt}={mac_val},{knw_fmt}={knw_fmt},n_errors={n_errors})"

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
            n_errors=self.n_errors
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

