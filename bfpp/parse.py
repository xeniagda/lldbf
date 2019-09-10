from tokens import *
from lark import Lark, Transformer


grammar = """
bfpp: bfpp_block+

?bfpp_block: bf_stmt
           | repetition
           | loc_dec
           | loc_goto

locname: /[\w\d_]+/
locname_active: ">" /[\w\d_]+/

loc_dec: "(?" locname* locname_active locname* ")"

loc_goto: "(!" locname ")"

repetition: cont_group INT

?cont_group: bfpp_block
           | "(" bfpp ")"

?bf_stmt: bf_basic_token
        | bf_loop

bf_loop: "[" bfpp "]"

!bf_basic_token: "+"
               | "-"
               | "<"
               | ">"
               | "."
               | ","

COMMENT: /\/\*.*\*\//

%import common.INT
%import common.WS
%ignore WS
%ignore COMMENT
"""

parser = Lark(grammar, start="bfpp")

class ParseTransformer(Transformer):
    def bfpp(self, blocks):
        return TokenList(blocks)

    def bfpp_block(self, args):
        return args

    def repetition(self, args):
        return Repetition(args[0], int(args[1]))

    def bf_basic_token(self, args):
        return BFToken(args[0])

    def bf_loop(self, args):
        return BFLoop(args[0])

    def locname(self, args):
        return ("ln", args[0].value)

    def locname_active(self, args):
        return ("ln_a", args[0].value)

    def loc_dec(self, args):
        locs = []
        active = -1
        for i, x in enumerate(args):
            if x[0] == "ln_a":
                active = i
            locs.append(x[1])
        return LocDec(locs, active)

    def loc_goto(self, args):
        return LocGoto(args[0][1])

if __name__ == "__main__":
    res = parser.parse("""
    (?>a b c)
    (!a) ++
    (!c) --
    <
    (!c) +++
    """)
    print(res)
    print(res.pretty())

    tokens = ParseTransformer().transform(res)
    print(repr(tokens))
    print(tokens.into_bf(Context()))
