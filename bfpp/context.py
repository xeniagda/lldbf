from collections import defaultdict
import copy

from cell_action import *

VERBOSE = True

# Difference between two states in the execution of a program.
class StateDelta:
    def __init__(self, ptr_delta=0):
        self.cell_actions = {} # {idx: cell_action}
        self.ptr_delta = ptr_delta
        self.ptr_id_delta = 0 # Sometimes, the pointer location becomes unknown. The pointer id is what the pointer delta is relative to

    def is_stable(self):
        return self.ptr_delta == self.ptr_id_delta == 0

    def with_appended(self, other):
        if other.ptr_id_delta != 0:
            # If the next delta makes the pointer indeterminate, what we know now is useless
            return other

        resulting = StateDelta()
        resulting.ptr_delta = self.ptr_delta + other.ptr_delta
        resulting.ptr_id_delta = self.ptr_id_delta

        resulting.cell_actions = {idx - self.ptr_delta: action for idx, action in self.cell_actions.items()}

        for idx, action in other.cell_actions.items():
            my_idx = idx - self.ptr_delta
            if idx in self.cell_actions:
                resulting.cell_actions[idx] = action.perform_after(resulting.cell_actions[idx])
            else:
                resulting.cell_actions[idx] = action

        return resulting

    def __str__(self):
        return f'StateDelta(actions={self.cell_actions}, Δptr={self.ptr_delta}, Δp_id={self.ptr_id_delta})'

    __repr__ = __str__

class State:
    def __init__(self):
        self.cell_values = defaultdict(int)
        self.ptr = 0
        self.ptr_id = 0

    def with_delta_applied(self, delta):
        result = State()

        if delta.ptr_id_delta != 0:
            result.cell_values = {}
            result.ptr = 0
            result.ptr_id = self.ptr_id + delta_ptr_id_delta

        for idx, action in delta.cell_actions.items():
            value = None
            if idx in self.cell_values:
                value = self.cell_values[idx]
            res_value = action.apply_to_value(value)
            result.cell_values[idx] = res_value

        return result

if __name__ == "__main__":
    # Ad-hoc tests
    delta1 = StateDelta()
    delta1.cell_actions[0] = Delta(None, 3)
    delta1.cell_actions[1] = Unknown(None)
    delta1.cell_actions[2] = Delta(None, 1)
    delta1.ptr_delta = 2

    delta2 = StateDelta()
    delta2.cell_actions[-1] = SetTo(None, 3)
    delta2.cell_actions[0] = SetTo(None, 3)

    print("delta1 =", delta1)
    print("delta2 =", delta2)
    print("delta1 o delta2 =", delta1.with_appended(delta2))
