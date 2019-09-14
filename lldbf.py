import sys
import ast
import time


def pad_start(st, wanted_len, padding=" "):
    if len(st) >= wanted_len:
        return st
    return padding * (wanted_len - len(st)) + st


def pad_end(st, wanted_len, padding=" "):
    if len(st) >= wanted_len:
        return st
    return st + padding * (wanted_len - len(st))


def hex_byte_signed(b, plus_for_positive=False):
    if b < 128:
        if plus_for_positive:
            return "+x" + pad_start(hex(b)[2:], 2, padding="0")
        return " x" + pad_start(hex(b)[2:], 2, padding="0")
    else:
        return "-x" + pad_start(hex(256 - b)[2:], 2, padding="0")


class Unit:
    JUMP_FORWARD_INVALID = -1
    INCDEC = 0
    MOV = 1
    JUMP_FORWARD = 2
    JUMP_BACKWARD = 3
    PRINT = 4
    READ = 5

    def __init__(self, typ, param):
        self.typ = typ
        self.param = param

    def __repr__(self):
        return "Unit(" + str(self) + ")"

    def __str__(self):
        if self.typ == Unit.JUMP_FORWARD_INVALID:
            return "INVALID ["
        if self.typ == Unit.INCDEC:
            if self.param == 1:
                return "+"
            if self.param == -1:
                return "-"
            if self.param > 256 - 30:
                return str(self.param - 256)
            if 0 < self.param < 30:
                return "+" + str(self.param)
            return hex_byte_signed(self.param, True)
        if self.typ == Unit.MOV:
            if self.param == 1:
                return ">"
            if self.param == -1:
                return "<"
            if self.param > 0:
                return ">" + str(self.param)
            return "<" + str(-self.param)
        if self.typ == Unit.JUMP_FORWARD:
            return "[ #" + str(self.param)
        if self.typ == Unit.JUMP_BACKWARD:
            return "] #" + str(self.param)
        if self.typ == Unit.PRINT:
            return "."
        if self.typ == Unit.READ:
            return ","


# Units: tuple of [type, *params]
# types:
#  -1 = unmatched [
#   0 = +/-, *params = number of pluses, or -number of minuses
#   1 = </>, *params = number of >, or -number of <
#   2 = [, *params = index of matching
#   3 = ], *params = index of matching
#   4 = .
#   5 = ,


def parse_code(code_str):
    code_units = []

    brack_stack = []
    last = ""
    idx = 0
    for ch in code_str:
        if ch in "+-":
            val = 1 if ch == "+" else 255
            if len(code_units) > 0 and code_units[-1].typ == Unit.INCDEC:
                code_units[-1].param += val
                code_units[-1].param %= 256
                if code_units[-1].param == 0:
                    code_units.pop()
                    idx -= 1
                continue
            else:
                code_units.append(Unit(Unit.INCDEC, val))

        elif ch in "<>":
            val = 1 if ch == ">" else -1
            if len(code_units) > 0 and code_units[-1].typ == Unit.MOV:
                code_units[-1].param += val
                if code_units[-1].param == 0:
                    code_units.pop()
                    idx -= 1

                continue
            else:
                code_units.append(Unit(Unit.MOV, val))
        elif ch == "[":
            code_units.append(Unit(Unit.JUMP_FORWARD_INVALID, None))
            brack_stack.append(idx)
        elif ch == "]":
            last_brack_idx = brack_stack.pop()
            code_units.append(Unit(Unit.JUMP_BACKWARD, last_brack_idx))
            code_units[last_brack_idx] = Unit(Unit.JUMP_FORWARD, idx)
        elif ch == ".":
            code_units.append(Unit(Unit.PRINT, None))
        elif ch == ",":
            code_units.append(Unit(Unit.READ, None))
        else:
            continue

        idx += 1
        last = ch

    return code_units


def pretty_print_code_slice(units,
                            start,
                            end,
                            cont_max_width=30,
                            graph_width=0,
                            depth_start=0,
                            mark_inst=-1):
    depth = depth_start
    lines = []

    nr_pad = len(str(end))

    max_depth = 0
    min_depth = graph_width

    i = start
    while i < end:
        graph = "| " * depth + "  " * (graph_width - depth)
        i_start = i

        special = False
        cont = None
        if units[i].typ == Unit.JUMP_FORWARD:
            graph = "| " * depth + ",-" + "--" * (graph_width - depth - 1)
            depth += 1
            if i == mark_inst:
                cont = "([)"
                special = True
            else:
                cont = "["
            i += 1
        elif units[i].typ == Unit.JUMP_BACKWARD:
            depth -= 1
            graph = "| " * depth + "`-" + "--" * (graph_width - depth - 1)
            if i == mark_inst:
                cont = "(])"
                special = True
            else:
                cont = "]"
            i += 1
        else:
            cont = ""
            while len(cont) < cont_max_width and i < end:
                if units[i].typ in [Unit.JUMP_FORWARD, Unit.JUMP_BACKWARD]:
                    break
                unit = str(units[i])
                if i == mark_inst:
                    unit = "(" + unit + ")"
                    special = True

                cont += pad_end(unit, 5, " ")

                i += 1

        line = pad_start(str(i_start), nr_pad, " ")
        if special:
            line = "*" + line
        else:
            line = " " + line

        lines.append((graph, line, cont))

        max_depth = max(max_depth, depth)
        min_depth = min(min_depth, depth)

    if max_depth > graph_width or min_depth < 0:
        return pretty_print_code_slice(units,
                                       start,
                                       end,
                                       cont_max_width,
                                       graph_width=max_depth - min_depth,
                                       depth_start=-min_depth,
                                       mark_inst=mark_inst)

    return lines


if __name__ == "__main__":
    if len(sys.argv) == 2:
        code_str = open(sys.argv[1]).read()

    code_units = parse_code(code_str)

    print(code_units)
    for graph, line, cont in pretty_print_code_slice(code_units,
                                                     0,
                                                     len(code_units),
                                                     mark_inst=0):
        print("\033[38;5;2m%s|\033[38;5;3m%s \033[0m%s" % (graph, line, cont))

    memory = []
    input_feed = []

    def get_mem(mp):
        global memory
        if mp < len(memory):
            return memory[mp]
        return 0

    def set_mem(mp, val):
        global memory
        if mp >= len(memory):
            memory += [0] * (mp - len(memory) + 1)
        memory[mp] = val % 256

    step_once = False
    last_line = ""

    def menu():
        global breakpoints, IP, output, step_once, last_line, input_feed, memory

        print("Output:", output)
        print("MP=", hex(MP))

        for graph, line, cont in pretty_print_code_slice(code_units,
                                                         max(0, IP - 5),
                                                         min(
                                                             len(code_units),
                                                             IP + 20),
                                                         mark_inst=IP):
            print("\033[38;5;2m%s|\033[38;5;3m%s \033[0m%s" %
                  (graph, line, cont))

        while True:
            cmd = input("> ")
            if cmd == "":
                cmd = last_line
                if last_line == "":
                    return

            if cmd[0] == "!":
                res = eval(cmd[1:])
                if res != None:
                    print("<", res)

            if cmd[0] == "c":
                return

            if cmd[0] == "s":
                step_once = True
                return

            if cmd[0] == "i":
                if len(cmd) == 1:
                    print("Use iw to set input, ia to append input and is to show input")
                else:
                    if cmd[1] == "s":
                        print("Input feed:")
                        for ch in input_feed:
                            if 32 <= ch < 128:
                                print(chr(ch), end="")
                            else:
                                print("\033[38;5;5m" + pad_start(hex(ch)[2:], 2, "0") + "\033[0m", end="")
                        print()
                    elif cmd[1] == "w":
                         set_input = ast.literal_eval(cmd[2:])
                         if type(set_input) == str:
                            input_feed = list(map(ord, set_input))
                         if type(set_input) == list:
                            input_feed = set_input

            if cmd[:2] == "ba":
                at = ast.literal_eval(cmd[2:])
                breakpoints = breakpoints | set([at])
                print("Breakpoints at", breakpoints)

            if cmd[0] == "d":
                exp = cmd[1:]

                if exp == "":
                    exp = "$-30,$+30"

                exp = exp.replace("$", str(IP))
                at = eval(exp)

                if type(at) == int:
                    start = at
                    end = at + 20
                else:
                    start, end = at

                start = max(0, start)
                end = max(len(code_units), start)

                for graph, line, cont in pretty_print_code_slice(
                        code_units,
                        start,
                        end,
                        mark_inst=IP):
                    print("\033[38;5;2m%s|\033[38;5;3m%s \033[0m%s" %
                          (graph, line, cont))

            if cmd[:2] == "bd":
                at = ast.literal_eval(cmd[2:])
                breakpoints = breakpoints.difference(set([at]))
                print("Breakpoints at", breakpoints)

            if cmd[:2] == "bl":
                print("Breakpoints at", breakpoints)

            if cmd[0] == "X":
                exp_pos, exp_val = cmd[1:].split(",")
                if exp_pos == "":
                    exp_pos = "$"
                exp_pos = exp_pos.replace("$", str(MP))

                at = eval(exp_pos)
                val = eval(exp_val)

                set_mem(at, val)

            if cmd[0] == "x":
                exp = cmd[1:]
                if exp == "":
                    exp = "$"

                exp = exp.replace("$", str(MP))

                at = eval(exp)

                if type(at) == int:
                    start = end = at
                else:
                    start, end = at

                start = max(0, start)
                end = max(0, end)

                start_block = start - start % 16
                end_block = (end + 16) - (end + 16) % 16

                last_mem = end_block - 1
                y_pad = len(hex(last_mem)) - 2

                print(" " * (y_pad + 4), end="")
                for x in range(16):
                    print("_" + hex(x)[2:], end="  ")
                print()
                for y in range(start_block // 16, end_block // 16):
                    print(pad_start(hex(y * 16)[2:], y_pad, padding="0")[:-1] +
                          "_",
                          "|",
                          end="")
                    for x in range(16):
                        addr = y * 16 + x
                        if addr == MP:
                            print("\033[7m", end="")
                        if addr < start or addr > end:
                            print("\033[2m", end="")

                        print(hex_byte_signed(get_mem(addr)), end="")

                        if addr == MP:
                            print("\033[0m", end="")
                        if addr < start or addr > end:
                            print("\033[0m", end="")

                    print(" | ", end="")
                    for x in range(16):
                        addr = y * 16 + x
                        if addr == MP:
                            print("\033[7m", end="")
                        if addr < start or addr > end:
                            print("\033[2m", end="")

                        val = get_mem(addr)

                        if val < 32 or val > 126:
                            print(".", end="")
                        else:
                            print(chr(get_mem(addr)), end="")

                        if addr == MP:
                            print("\033[0m", end="")

                        if addr < start or addr > end or val == 0:
                            print("\033[0m", end="")


                    print()
            last_line = cmd

    IP = 0
    MP = 0

    breakpoints = set()

    print("Enter breakpoints:")
    bps = input()
    if bps != "":
        bps = ast.literal_eval(bps)

        if type(bps) == "tuple":
            breakpoints = set(bps)
        else:
            breakpoints = set([bps])

    breakpoints = breakpoints | set([len(code_units)])

    output = []

    def run_instruction():
        global IP, MP, output, input
        if code_units[IP].typ == Unit.INCDEC:
            set_mem(MP, (get_mem(MP) + code_units[IP].param) % 256)
            IP += 1

        elif code_units[IP].typ == Unit.MOV:
            MP += code_units[IP].param
            IP += 1

        elif code_units[IP].typ == Unit.JUMP_FORWARD:
            if get_mem(MP) == 0:
                IP = code_units[IP].param + 1
            else:
                IP += 1

        elif code_units[IP].typ == Unit.JUMP_BACKWARD:
            if get_mem(MP) != 0:
                IP = code_units[IP].param + 1
            else:
                IP += 1

        elif code_units[IP].typ == Unit.PRINT:
            output += [get_mem(MP)]
            print(chr(get_mem(MP)), end="", flush=True)
            IP += 1

        elif code_units[IP].typ == Unit.READ:
            if len(input_feed) == 0:
                print(", reached without input left.")
                print("Use the i command to supply input")
                menu()
            else:
                set_mem(MP, input_feed[0])
                input_feed = input_feed[1:]
                IP += 1
        else:
            IP += 1

    while IP <= len(code_units):
        try:
            if IP in breakpoints:
                print("\nHit breakpoint {}".format(IP))
                menu()

            if step_once:
                step_once = False
                menu()

            if IP == len(code_units):
                break

            run_instruction()
        except KeyboardInterrupt as _:
            menu()
