from collections import defaultdict
import copy

from cell_action import *

VERBOSE = True

# Difference between two states in the execution of a program.
# a @ b = apply a, then apply b
class StateDelta:
    def __init__(self, ptr_delta=0):
        self.cell_actions = {} # {idx: cell_action}
        self.ptr_delta = ptr_delta
        self.ptr_id_delta = 0 # Sometimes, the pointer location becomes unknown. The pointer id is what the pointer delta is relative to

    def do_action(action):
        st = StateDelta()
        st.cell_actions[0] = action
        return st

    def is_stable(self):
        return self.ptr_delta == self.ptr_id_delta == 0

    def __matmul__(self, other):
        if other.ptr_id_delta != 0:
            # If the next delta makes the pointer indeterminate, what we know now is useless
            return other

        resulting = StateDelta()
        resulting.ptr_delta = self.ptr_delta + other.ptr_delta
        resulting.ptr_id_delta = self.ptr_id_delta

        resulting.cell_actions = self.cell_actions.copy()

        for idx, action in other.cell_actions.items():
            my_idx = idx + self.ptr_delta
            if my_idx in self.cell_actions:
                resulting.cell_actions[my_idx] = action.perform_after(self.cell_actions[my_idx])
            else:
                resulting.cell_actions[my_idx] = action

        return resulting

    def copy(self):
        res = StateDelta()
        res.cell_actions = self.cell_actions.copy()
        res.ptr_delta = self.ptr_delta
        res.ptr_id_delta = self.ptr_id_delta
        return res

    def repeated(self):
        res = StateDelta()
        if self.ptr_delta == 0 and self.ptr_id_delta == 0:
            res.cell_actions = {idx: action.repeated() for idx, action in self.cell_actions.items()}
            return res

        res.ptr_delta = 0
        res.ptr_id_delta = self.ptr_id_delta + 1

        return res

    def __str__(self):
        return f'StateDelta(actions={self.cell_actions}, Δptr={self.ptr_delta}, Δp_id={self.ptr_id_delta})'

    __repr__ = __str__

class State:
    def __init__(self):
        self.cell_values = defaultdict(int)
        self.ptr = 0
        self.ptr_id = 0

        self.macros = {}
        self.named_locations = {} # {name: idx}

    def with_delta_applied(self, delta):
        result = State()
        result.ptr = self.ptr + delta.ptr_delta
        result.ptr_id = self.ptr_id
        result.named_locations = self.named_locations.copy()
        result.cell_values = self.cell_values.copy()

        if delta.ptr_id_delta != 0:
            result.cell_values = defaultdict(lambda: None)
            result.ptr = 0
            result.ptr_id = self.ptr_id + delta.ptr_id_delta
            result.named_locations = {}

        for idx, action in delta.cell_actions.items():
            idx = idx + result.ptr
            value = self.cell_values[idx]

            res_value = action.apply_to_value(value)
            result.cell_values[idx] = res_value

        return result

    def __str__(self):
        return f'State(vals={dict(self.cell_values)}, default={self.cell_values[None]} ptr={self.ptr}, ptr_id={self.ptr_id}, locs={self.named_locations})'

if __name__ == "__main__":
    # Ad-hoc tests
    delta1 = StateDelta()
    delta1.cell_actions[0] = Delta(None, 3)
    delta1.cell_actions[1] = Unknown(None)
    delta1.cell_actions[2] = Delta(None, 1)
    delta1.cell_actions[3] = SetTo(None, 7)
    delta1.ptr_delta = 2

    delta2 = StateDelta()
    delta2.cell_actions[-1] = SetTo(None, 3)
    delta2.cell_actions[0] = SetTo(None, 3)

    print("delta1 =", delta1)
    print("delta2 =", delta2)
    print("delta1 o delta2 =", delta1 @ delta2)

    print("delta2^inf =", delta2.repeated())
