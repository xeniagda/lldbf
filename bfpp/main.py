from sys import argv
from preproc import preproc_file
from parse import parse
from tokens import Context
from postproc import postproc

if len(argv) == 2:
    # Read file
    code = preproc_file(argv[1])
else:
    print("Please provide a file!")
    exit()

tokens = parse(argv[1], code)
print(postproc(tokens.into_bf(Context())))
