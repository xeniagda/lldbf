import os
from tokens import *
from lark import Lark, Transformer, v_args
from bfppfile import BFPPFile, Span
from error import *

grammar = r"""

main: block+

block: bftoken
     | repetition
     | loc_dec
     | loc_goto
     | dec_macro
     | run_macro
     | loop
     | preproc_directive
     | debug
     | _paren_group

_paren_group: "(" main ")"

!bftoken: "+"
        | "-"
        | "<"
        | ">"
        | "."
        | ","

repetition: block INT

locname: /[\w\d_]+/

loc_dec_bare: "(" locname ("," locname) * ")" "at" locname

loc_dec: "declare" loc_dec_bare

loc_goto: "to" locname

dec_macro: "def" locname loc_dec_bare "{" main "}"

run_loc: "(" locname ("," locname) * ")"
run_macro: "run" locname run_loc

stable_loop: "[" main "]"
unstable_loop: "unstable" "[" main "]"

loop: stable_loop
    | unstable_loop

?path: /[\w.\/]+/

include: "#" "include" path

preproc_directive: include
debug: "debug"

COMMENT: "/*" /(.|\n)*?/ "*/"
       | "//" /.*/

%import common.INT
%import common.WS
%ignore COMMENT
%ignore WS
"""

parser = Lark(grammar, start="main", propagate_positions=True)


class ParseTransformer(Transformer):
    def __init__(self, bfile):
        self.bfile = bfile

    def meta2span(self, meta):
        return Span(self.bfile, meta.start_pos, meta.end_pos)

    @v_args(meta=True)
    def main(self, args, meta):
        return TokenList(self.meta2span(meta), args)

    def block(self, args):
        return args[0]

    @v_args(meta=True)
    def bftoken(self, args, meta):
        return BFToken(self.meta2span(meta), args[0])

    @v_args(meta=True)
    def repetition(self, args, meta):
        return Repetition(self.meta2span(meta), args[0], int(args[1]))

    def locname(self, args):
        return args[0].value

    @v_args(meta=True)
    def loc_dec_bare(self, args, meta):
        *names, active = args

        if active not in names:
            err = DeclareLocnameNotFound(self.meta2span(meta), active, names)
            err.show()
            idx = 0
        else:
            idx = names.index(active)

        return (names, idx)

    @v_args(meta=True)
    def loc_dec(self, args, meta):
        names, idx = args[0]

        return LocDec(self.meta2span(meta), names, idx)

    @v_args(meta=True)
    def loc_goto(self, args, meta):
        name = args[0]

        return LocGoto(self.meta2span(meta), name)

    @v_args(meta=True)
    def dec_macro(self, args, meta):
        mac_name, (names, idx), code = args

        locdec = LocDec(self.meta2span(meta), names, idx)

        return DeclareMacro(self.meta2span(meta), mac_name, locdec, code)

    def run_loc(self, args):
        return args

    @v_args(meta=True)
    def run_macro(self, args, meta):
        name, args = args

        return InvokeMacro(self.meta2span(meta), name, args)

    def stable_loop(self, args):
        return True, args[0]

    def unstable_loop(self, args):
        return False, args[0]

    @v_args(meta=True)
    def loop(self, args, meta):
        stable, cont = args[0]

        return BFLoop(self.meta2span(meta), stable, cont)

    def include(self, args):
        path = args[0]
        folder = os.path.dirname(self.bfile.name)
        inc_filepath = os.path.join(folder, path)

        return parse(path, open(inc_filepath).read())

    def preproc_directive(self, args):
        return args[0]

def parse(filename, code):
    bfile = BFPPFile(filename, code)

    parsed = parser.parse(code)
    tokens = ParseTransformer(bfile).transform(parsed)

    return tokens

if __name__ == "__main__":
    tokens = parse("print_zts.bfpp", """\

def add48(val, temp) at temp {
    +6 [
        to val +8
        to temp -
    ]
}

declare (n, tmp) at n

run add48(n, tmp)

to n .

    """)
    print(repr(tokens))
    print(tokens.into_bf(State()))
