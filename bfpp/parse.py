import os
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
           | assume_stable
           | inv_macro
           | directive
           | debug

locname: /[\w\d_]+/

locname_inactive: locname
locname_active: ">" locname

loc_dec: "(?" locname_inactive* locname_active locname_inactive* ")"

loc_goto: "(!" locname ")"

dec_macro: "def" locname loc_dec "{" bfpp "}"

inv_macro: "inv" locname "(" locname* ")"

assume_stable: "assume" "stable" "{" bfpp* "}"

repetition: cont_group INT

?cont_group: bfpp_block
           | "(" bfpp ")"

?bf_stmt: bf_basic_token
        | stable_loop
        | unstable_loop

stable_loop: "[" bfpp "]"
unstable_loop: "unstable" "[" bfpp "]"

!bf_basic_token: "+"
               | "-"
               | "<"
               | ">"
               | "."
               | ","

?directive: include

include: "#" "include" path

?path: /[\w.]+/

debug: "debug"

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

    @v_args(meta=True)
    def bfpp(self, blocks, meta):
        return TokenList(self.meta2span(meta), blocks)

    def bfpp_block(self, args):
        return args

    @v_args(meta=True)
    def repetition(self, args, meta):
        return Repetition(self.meta2span(meta), args[0], int(args[1]))

    @v_args(meta=True)
    def bf_basic_token(self, args, meta):
        return BFToken(self.meta2span(meta), args[0])

    @v_args(meta=True)
    def stable_loop(self, args, meta):
        return BFLoop(self.meta2span(meta), True, args[0])

    @v_args(meta=True)
    def unstable_loop(self, args, meta):
        return BFLoop(self.meta2span(meta), False, args[0])

    def locname(self, args):
        return args[0].value

    def locname_inactive(self, args):
        return ("ln", args[0])

    def locname_active(self, args):
        return ("ln_a", args[0])

    @v_args(meta=True)
    def loc_dec(self, args, meta):
        locs = []
        active = -1
        for i, x in enumerate(args):
            if x[0] == "ln_a":
                active = i
            locs.append(x[1])
        return LocDec(self.meta2span(meta), locs, active)

    @v_args(meta=True)
    def loc_goto(self, args, meta):
        return LocGoto(self.meta2span(meta), args[0])

    @v_args(meta=True)
    def dec_macro(self, args, meta):
        name, args, content = args

        return DeclareMacro(self.meta2span(meta), name, args, content)

    @v_args(meta=True)
    def inv_macro(self, args, meta):
        fn_name = args[0]
        args_for_function = args[1:]

        return InvokeMacro(self.meta2span(meta), fn_name, args_for_function)

    @v_args(meta=True)
    def debug(self, args, meta):
        return Debug(self.meta2span(meta))

    @v_args(meta=True)
    def assume_stable(self, args, meta):
        return AssumeStable(self.meta2span(meta), args[0])

    def include(self, args):
        path = args[0]
        folder = os.path.dirname(self.bfile.name)
        inc_filepath = os.path.join(folder, path)

        return parse(path, open(inc_filepath).read())

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

    > 3
    (?x >y i j k z)
    inv add69(x y)
    inv add65(i y)
    inv add66(j k)
    inv add67(k z)

    inv print_clear_zts(y)

    """)
    print(repr(tokens))
    print(tokens.into_bf(Context()))
