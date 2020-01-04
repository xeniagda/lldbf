from sys import argv
from parse import parse
from context import State
from postproc import postproc
from init_macros import INIT_MACROS
from init_types import INIT_TYPES

def compile_path_to_str(path):
    code = open(path, "r").read()
    tokens = parse(path, code)

    ctx = State()
    ctx.macros = INIT_MACROS
    ctx.types = INIT_TYPES

    res = tokens.into_bf(ctx)

    if ctx.n_errors == 0:
        return postproc(res)
    else:
        print("Compilation failed due to", ctx.n_errors, "errors")
        exit()

if __name__ == "__main__":
    if len(argv) == 2:
        # Read file
        path = argv[1]
    else:
        print("Please provide a file!")
        exit()

    compiled = compile_path_to_str(path)
    print(compiled)
