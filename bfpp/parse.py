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
     | assume_stable
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

varname: /[\w\d_]+/
path: varname ("." varname)*

loc_dec_bare: "(" varname ("," varname) * ")" "at" path

loc_dec: "declare" loc_dec_bare

loc_goto: "to" path

dec_macro: "def" varname loc_dec_bare "{" main "}"

run_args: "(" path ("," path) * ")"
run_macro: "run" varname run_args

stable_loop: "[" main "]"
unstable_loop: "unstable" "[" main "]"

loop: stable_loop
    | unstable_loop

assume_stable: "assume" "stable" "{" main "}"

?filepath: /[\w.\/]+/

include: "#" "include" filepath

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

    def varname(self, args):
        return args[0].value

    @v_args(meta=True)
    def path(self, args, meta):
        return Path(self.meta2span(meta), args)

    @v_args(meta=True)
    def loc_dec_bare(self, args, meta):
        *names, active = args

        return LocDecBare(self.meta2span(meta), names, active)

    @v_args(meta=True)
    def loc_dec(self, args, meta):
        bare = args[0]

        return LocDec(self.meta2span(meta), bare)

    @v_args(meta=True)
    def loc_goto(self, args, meta):
        path = args[0]
        return LocGoto(self.meta2span(meta), path)

    @v_args(meta=True)
    def dec_macro(self, args, meta):
        mac_name, bare, code = args

        return DeclareMacro(self.meta2span(meta), mac_name, bare, code)

    def run_args(self, args):
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

    @v_args(meta=True)
    def assume_stable(self, args, meta):
        cont = args[0]

        return AssumeStable(self.meta2span(meta), cont)

    def include(self, args):
        path = args[0]
        folder = os.path.dirname(self.bfile.name)
        inc_filepath = os.path.join(folder, path)

        return parse(path, open(inc_filepath).read())

    def preproc_directive(self, args):
        return args[0]

    @v_args(meta=True)
    def debug(self, args, meta):
        return Debug(self.meta2span(meta))

def parse(filename, code):
    bfile = BFPPFile(filename, code)

    parsed = parser.parse(code)
    tokens = ParseTransformer(bfile).transform(parsed)

    return tokens

if __name__ == "__main__":
    tokens = parse("print_zts.bfpp", """\

def add32(n, tmp) at tmp {
    +8
    [
        to n +4
        to tmp -
    ]
}

declare (a, b) at b

run add32(a, b)

    """)
    print(repr(tokens))
    print(tokens)
    print(tokens.into_bf(State()))
