from collections import defaultdict

from cell_action import *

MULTILINE_CTX = True
SHOW_CTX_STACK = False
SHOW_MACROS = False
SHOW_KNOWN = True

class LocalContext:
    def __init__(self, origin, named_locations, inv_id):
        self.inv_id = inv_id
        self.origin = origin
        self.current_ptr = origin
        self.cell_actions = defaultdict(lambda: Delta(0)) # idx: CellAction

        self.named_locations = named_locations

        self.in_macro = False

    def apply_action(self, action):
        self.cell_actions[self.current_ptr] = action.perform_after(self.cell_actions[self.current_ptr])

    def is_stable_relative_to(self, other):
        return self.current_ptr == self.origin and self.inv_id == other.inv_id

    def copy(self):
        res = LocalContext(self.origin, self.named_locations.copy(), self.inv_id)
        res.current_ptr = self.current_ptr
        res.modified_cells = self.modified_cells
        res.in_macro = self.in_macro

        return res

    def __str__(self):
        return "LocalContext(o={},ptr={},actions={},locs={},inv_id={})".format(
            self.origin,
            self.current_ptr,
            dict(self.cell_actions),
            self.named_locations,
            self.inv_id,
        )

    __repr__ = __str__

class Context:
    def __init__(self):
        self.lctx_stack = [LocalContext(0, {}, 0)]

        self.macros = {}

        self.known_values = defaultdict(lambda: 0)

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
            knw_val = str(dict(self.known_values))
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
        res = LocalContext(
            self.lctx().current_ptr,
            self.lctx().named_locations.copy(),
            self.lctx().inv_id
        )
        res.in_macro = self.lctx().in_macro
        return res

    def copy(self):
        res = Context()
        res.lctx_stack = [lctx.copy() for lctx in self.lctx_stack]
        res.macros = self.macros.copy()
        res.known_values = self.known_values.copy()

        return res

    def pop_lctx(self, repeated):
        at = self.lctx().current_ptr
        inv_id = self.lctx().inv_id
        stable = self.lctx().is_stable_relative_to(self.lctx_stack[-2])

        cell_actions = self.lctx().cell_actions

        self.lctx_stack.pop()

        if inv_id != self.lctx().inv_id:
            self.lctx().named_locations = {}
            self.lctx().inv_id = inv_id

        for loc, act in cell_actions.items():
            if repeated:
                act = act.repeated()
                self.known_values[loc] = act.apply_to_value(self.known_values[loc])

            self.lctx().cell_actions[loc] = act.perform_after(self.lctx().cell_actions[loc])

        if repeated and not stable:
            self.lctx().cell_actions.clear()
            self.known_values = defaultdict(lambda: None)

        self.lctx().current_ptr = at

    def apply_action(self, action):
        self.known_values[self.lctx().current_ptr] = action.apply_to_value(self.known_values[self.lctx().current_ptr])
        self.lctx().apply_action(action)
