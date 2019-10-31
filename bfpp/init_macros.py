from add_n_gen import precomp_xyzk_list
from tokens import *

INIT_MACROS = {}

# Generate setN
for i in range(256):
    (x, y, z, k) = precomp_xyzk_list[i]

    if y == z:
        fn_body = TokenList(PREGEN_SPAN, [
            LocGoto(PREGEN_SPAN, "res"),
            inc_by(k + x),
        ])
    elif y == 0:
        fn_body = TokenList(PREGEN_SPAN, [
            LocGoto(PREGEN_SPAN, "res"),
            inc_by(k),
        ])
    else:
        fn_body = TokenList(PREGEN_SPAN, [
            LocGoto(PREGEN_SPAN, "tmp"),
            inc_by(x),
            BFLoop(
                None,
                True,
                TokenList(PREGEN_SPAN, [
                    LocGoto(PREGEN_SPAN, "res"),
                    inc_by(y),
                    LocGoto(PREGEN_SPAN, "tmp"),
                    inc_by(-z),
                ])),
            LocGoto(PREGEN_SPAN, "res"),
            inc_by(k),
        ])

    args = LocDec(PREGEN_SPAN, ["res", "tmp"], 1)

    fn = DeclareMacro(PREGEN_SPAN, "add" + str(i), args, fn_body)
    INIT_MACROS["add" + str(i)] = fn

    dec_n = 256 - i
    if i == 0:
        dec_n = 0
    fn = DeclareMacro(PREGEN_SPAN, "dec" + str(dec_n), args, fn_body)
    INIT_MACROS["dec" + str(dec_n)] = fn

