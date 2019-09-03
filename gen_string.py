import sys

divs_mod_256 = {}

for i in range(256):
    n = 1

    res = 0
    while True:
        n = (n - i) % 256
        res += 1

        if n == 0:
            divs_mod_256[i] = res
            break
        if n == 1:
            break


def abs256(x):
    x %= 256
    return min(x, 256 - x)


def smallest256(x):
    x %= 256
    if x < 128:
        return x
    else:
        return x - 256


def go_to_val_from(current_val, to):
    best = None
    best_score = 1e10

    for cur_change in range(-15, 16):
        for mult in range(-15, 16):
            for div in range(-15, 16):
                if div == 0:
                    continue

                if div in divs_mod_256:
                    res_val = (current_val +
                               cur_change) * mult * divs_mod_256[div] % 256
                else:
                    continue

                post_change = to - res_val

                post_change = smallest256(post_change)

                score = abs256(cur_change) + abs256(mult) + abs256(post_change) + abs256(div)
                if mult == 0:
                    score -= 1
                if mult == 1:
                    score -= 6

                if score <= best_score:
                    best = (cur_change, mult, div, post_change)
                    best_score = score

    return best


def bf_add(val):
    if val < 0:
        return "-" * -val
    else:
        return "+" * val


def gen_code(cur_change, mult, div, post_change, cur_left):
    if cur_left:
        return bf_add(cur_change) + "[>" + bf_add(mult) + "<" + bf_add(
            -div) + "]>" + bf_add(post_change)
    else:
        return bf_add(cur_change) + "[<" + bf_add(mult) + ">" + bf_add(
            -div) + "]<" + bf_add(post_change)

if __name__ == "__main__":
    continue_after_end = True
    if len(sys.argv) == 2:
        wanted_string = sys.argv[1]
        continue_after_end = False
    else:
        wanted_string = input()

    cur_val = 0

    cur_left = True

    out = ""

    while True:
        n = ord(wanted_string[0])
        wanted_string = wanted_string[1:]
        c_ch, m, div, p_ch = go_to_val_from(cur_val, n)
        print(cur_val, "to", n, "=", chr(n), "->", c_ch, m, div, p_ch, file=sys.stderr)

        if m == 0:
            out = "[-]" + bf_add(p_ch)
        elif m == div:
            out = bf_add(c_ch + p_ch)
        else:
            out = gen_code(c_ch, m, div, p_ch, cur_left)
            cur_left = not cur_left

        print(out + ".", end="", flush=True)

        cur_val = n

        if len(wanted_string) == 0:
            if continue_after_end:
                print()
                try:
                    wanted_string = "\n" + input()
                except EOFError as _:
                    break
            else:
                break

    print()
