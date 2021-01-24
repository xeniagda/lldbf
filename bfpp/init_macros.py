from add_n_gen import precomp_xyzk_list
from tokens import *

INIT_MACROS = {}

PREGEN_SPAN = Span(BFPPFile("PREGENERATED", ""), 0, 0)

def inc_by(n):
    n = n % 256
    if n == 0:
        return TokenList(PREGEN_SPAN, [])
    if n < 128:
        return Repetition(None, BFToken(PREGEN_SPAN, "+"), n)
    else:
        return Repetition(None, BFToken(PREGEN_SPAN, "-"), 256 - n)

# Generate setN
for i in range(256):
    (x, y, z, k) = precomp_xyzk_list[i]

    clear_tmp = TokenList(PREGEN_SPAN, [
        LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["tmp"])),
        BFLoop(PREGEN_SPAN, True, BFToken(PREGEN_SPAN, "-")),
    ])

    clear_res = TokenList(PREGEN_SPAN, [
        LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["res"])),
        BFLoop(PREGEN_SPAN, True, BFToken(PREGEN_SPAN, "-")),
    ])

    for do_set in [True, False]:
        if y == z:
            fn_body = TokenList(PREGEN_SPAN, [
                # clear_tmp,
                LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["res"])),
                inc_by(k + x),
            ])
        elif y == 0:
            fn_body = TokenList(PREGEN_SPAN, [
                # clear_tmp,
                LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["res"])),
                inc_by(k),
            ])
        else:
            fn_body = TokenList(PREGEN_SPAN, [
                clear_tmp,
                LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["tmp"])),
                inc_by(x),
                BFLoop(
                    None,
                    True,
                    TokenList(PREGEN_SPAN, [
                        LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["res"])),
                        inc_by(y),
                        LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["tmp"])),
                        inc_by(-z),
                    ])),
                LocGoto(PREGEN_SPAN, Path(PREGEN_SPAN, ["res"])),
                inc_by(k),
            ])

        if do_set:
            fn_body.tokens.insert(0, clear_res)

        args = LocDecBare(PREGEN_SPAN, [("res", "Byte"), ("tmp", "Byte")], (None, Path(PREGEN_SPAN, ["tmp"])))

        if do_set:
            fn = DeclareMacro(PREGEN_SPAN, "set" + str(i), args, fn_body)
            INIT_MACROS["set" + str(i)] = fn
        else:
            fn = DeclareMacro(PREGEN_SPAN, "add" + str(i), args, fn_body)
            INIT_MACROS["add" + str(i)] = fn

            dec_n = 256 - i
            if i == 0:
                dec_n = 0
            fn = DeclareMacro(PREGEN_SPAN, "dec" + str(dec_n), args, fn_body)
            INIT_MACROS["dec" + str(dec_n)] = fn

