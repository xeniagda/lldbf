from tokens import *
from lark import Lark, Transformer, v_args
from bfppfile import BFPPFile, Span

grammar = r"""
bfpp: bfpp_block+

?bfpp_block: bf_stmt
           | repetition
           | loc_dec
           | loc_goto
           | dec_macro
           | inv_macro

locname: /[\w\d_]+/

locname_inactive: locname
locname_active: ">" locname

loc_dec: "(?" locname_inactive* locname_active locname_inactive* ")"

loc_goto: "(!" locname ")"

dec_macro: "def" locname loc_dec "{" bfpp "}"

inv_macro: "inv" locname "(" locname* ")"

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

COMMENT: "/*" /(.|\n)*?/ "*/"
       | "//" /.*/

%import common.INT
%import common.WS
%ignore COMMENT
%ignore WS
"""

parser = Lark(grammar, start="bfpp", propagate_positions=True)


class ParseTransformer(Transformer):
    def __init__(self, bfile):
        self.bfile = bfile

    def meta2span(self, meta):
        return Span(self.bfile, meta.start_pos, meta.end_pos)

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
        return args[0].value

    def locname_inactive(self, args):
        return ("ln", args[0])

    def locname_active(self, args):
        return ("ln_a", args[0])

    def loc_dec(self, args):
        locs = []
        active = -1
        for i, x in enumerate(args):
            if x[0] == "ln_a":
                active = i
            locs.append(x[1])
        return LocDec(locs, active)

    def loc_goto(self, args):
        return LocGoto(args[0])

    def dec_macro(self, args):
        name, args, content = args

        return DeclareMacro(name, args, content)

    def inv_macro(self, args):
        fn_name = args[0]
        args_for_function = args[1:]

        return InvokeMacro(fn_name, args_for_function)

def parse(filename, code):
    bfile = BFPPFile(filename, code)

    parsed = parser.parse(code)
    tokens = ParseTransformer(bfile).transform(parsed)

    return tokens

if __name__ == "__main__":
    tokens = parse("print_zts.bfpp", """
    def print_clear_zts (?>start) {
        (!start) [-]

        >
        [.>]<
        [<]
    }

    >>>
    (?x >y i j k z)
    inv add69(x y)
    inv add65(i y)
    inv add66(j k)
    inv add67(k z)

    inv print_clear_zts(y)

    """)
    print(repr(tokens))
    print(tokens.into_bf(Context()))
