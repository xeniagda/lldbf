from sys import argv
from parse import *

if len(argv) == 2:
    # Read file
    code = open(argv[1]).read()
else:
    print("Please provide a file!")
    exit()

res = parser.parse(code)
tokens = ParseTransformer().transform(res)
print(tokens.into_bf(Context()))
