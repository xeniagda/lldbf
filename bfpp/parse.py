from tokens import *
from lark import Lark, Transformer


grammar = """
bfpp: bfpp_block+

?bfpp_block: bf_stmt
           | repetition
           | loc_decs

locname: /\w+/

loc_decs: "(" locname* "*" locname locname* ")"

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

%import common.INT
%import common.WS
%ignore WS
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

res = parser.parse("+++ ([+>]-)5")
print(res)
print(res.pretty())

tokens = ParseTransformer().transform(res)
print(repr(tokens))
print(tokens.into_bf(Context()))
