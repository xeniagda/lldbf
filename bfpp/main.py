from sys import argv
from parse import parse
from context import State
from postproc import postproc
# from init_macros import INIT_MACROS

if len(argv) == 2:
    # Read file
    code = open(argv[1], "r").read()
else:
    print("Please provide a file!")
    exit()

tokens = parse(argv[1], code)

ctx = State()
# ctx.macros = INIT_MACROS

res = tokens.into_bf(ctx)

#if ctx.n_errors == 0:
print(postproc(res))
