from sys import argv
from parse import parse
from tokens import Context
from postproc import postproc

if len(argv) == 2:
    # Read file
    code = open(argv[1], "r").read()
else:
    print("Please provide a file!")
    exit()

tokens = parse(argv[1], code)
print(postproc(tokens.into_bf(Context())))
