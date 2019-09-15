from sys import argv
from preproc import preproc_file
from parse import *
from postproc import postproc

if len(argv) == 2:
    # Read file
    code = preproc_file(argv[1])
else:
    print("Please provide a file!")
    exit()

res = parser.parse(code)
tokens = ParseTransformer().transform(res)
print(postproc(tokens.into_bf(Context())))
