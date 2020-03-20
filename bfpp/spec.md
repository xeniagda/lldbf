# BFPP


BFPP (brainfuck preprocessor) is a language mostly backwards compatible with regular brainfuck, but with some significant improvements and features.

## Named locations / variables

Variables in bfpp are just locations in the memory with names. Variables are relative to the current "frame", so for example entering an unstable loop
(a loop which does not always start on the same cell, will be further explained below) removes all variables, as the preprocessor can't know where they
are relative to the current frame.

Declaring variables works using the following syntax:

```
declare (variablename_0: datatype_0, variablename_1: datatype_1, ...) at variablename_n;
```

This declares a contigouos set of variables, located in memory so that the cursor points to `variablename_n`.

The standard datatype is `cell`, which is just a regular cell in brainfuck. If a variable has type `cell`, the `: datatype` can be left out.

To use a variable, you move the cursor to it like this:

```
declare (a: cell, b: cell) at a;

to b

+++
```

Here, we declare a variable `a` at the cursor, and a variable `b`, one cell right of the cursor. `to b` moves the cursor to `b` and compiles to the
`>`-instruction. We then add 3 to `b` using `+++`, which works just like in brainfuck.

If we want to declare a variable relative to other variables, the following syntax works:

```
declare (datatype_0 variablename_0, ...) with variablename_n at previous_variablename
```

Here, `previous_variablename` is a variable which has been declared before, and it puts the new variables in a way such that `variablename_n` ends up
at the same location as `previous_variablename`.

## Loops

Loops in bfpp come in two kinds. The stable loop, and the unstable loop.

A stable loop is a loop in where the cursor is at the same location in the beginning and end of the loop. This means that the compiler can assume that
all variables stay in the same location. This means that variables declared before the loop can be accessed from within the loop.

The syntax for stable loops are just like normal loops in brainfuck. Stable loops can only contain other stable loops, not unstable loops.

Unstable loops are loops where the cursor is not necessarily at the same location in the beginning and end of the loop. An example of this could be
`[>]`, where the cursor ends up one cell to the right of where it starts. As the cursor is not the same in each iteration, named locations become
unavailable. All variables before the loop is defined will be removed, and also unavailable after the loop.

Unstable loops need to be marked as such, which you do by prefixing the loop with the `unstable` keyword. While the compiler is smart enough to perfectly
figure out which loops are stable and unstable by itself, this aids readability and gives much better error messages, as one might intend to make a
stable loop, but mistakenly makes it unstable, or vice versa.

Sometimes, one can have multiple unstable loops, which in the end cancel eachother out and creates a stable piece of code altogether. In this case, one
can mark the block with the `assume stable` keyword to make the compiler assume that the block is stable. As the compiler makes no attempt to verify this
assumtion, the resulting output might be invalid if the programmer makes a mistake.

One big feature of BFPP is the elimination of unreachable loops. BFPP keeps track of all the known values in memory it can, and if a value is garuanteed
to be zero before a loop, that loop will never be executed and as such will not be put into the output. The compiler gives a warning in that case, as it
was probably a mistake to include a loop which will not be executed. (One exception is if a loop is within a function, which will be exlained below).

## Functions (really just macros)

BFPP has a fairly advanced macro system, where the macros act as compile time functions and as such will be referred to as functions. A function takes
a number of arguments, which are just varibles, and generates some code. The syntax for declaring a function is:

```
def functionname(arg_0: type_0, arg_1: type_1, ...) at arg_n {
    CODE
}
```

Inside the function, every argument acts just like a regular variable.

To invoke a function, the syntax is:

```
run functionname(arg_0, arg_1, ...)
```

The compiler makes sure the type of each argument is correct and gives an error if not.

As the functions in BFPP are really just glorified macros, and as there is no concept of calling in brainfuck, all functions are inlined, recursion
is not supported.

As BFPP keeps track of unreachable loops, one can zero all temporary variables passed to a function without worrying that the generated code will be
inefficient.

## Types

BFPP offers a fairly weak type system. The basic type, as previously mentioned, is the `cell`. One can create a type using the `struct` keyword:

```
struct TypeName {
    member_0: type_0,
    member_1: type_1,
    ...
}
```

If a variable has a struct type, one can use the syntax `variable.member` to access a member of the struct. The `to variable` syntax only works for
variables of type `cell`, but you can go to members of a variable too, like `to variable.member`.

## Other stuff

### Importing other files

One can include other files, by using the `#include`-command. The syntax is as follows:

```
#include file.bfpp
```

### Trivial optimizations

After generating the resulting brainfuck code, BFPP runs a simple pass on it, removing all instances of no-ops, like `+-`, `<>`, etc.

This means that doing:

```
to a
to b
```

is always optimized into `to b` in practise.

### Debugging

The `debug`-command does two things. Firtsly, it prints a bit of debug information to the console while compiling. Secondly, it includes a
`#`-instruction in the output. This is nonstandard and not supported by many interpreters, but is used in for example https://copy.sh/brainfuck
to dump all memory.

### Command repetition

Doing a command and following it with a number simply repeats the command that many times. Commands can be grouped by parentheses.

### Error messages

All tokens in BFPP keep track of where they came from in the source code, and as such errors always point to some part of the source when displayed.

### Standard library

There is a very light standard library BFPP. Parts of it come from the `code/std.bfpp`-file, other parts are generated.

A few notable functions are:

* `decn(var: cell, tmp: cell)` / `addn(var: cell, tmp: cell)` where `n` is some number subtracts or adds `n` to the variable in an efficient way.
* `copy(source: cell, dest: cell, tmp: cell)`: Copies values.

## Example code:

Example code can be found in the `bfpp/code/` directory. Some notable examples are:

* `str_cmp.bfpp`: A string comparison algorithm. This is a quite simple, but very nontrivial program to write in brainfuck, as you need to manage memory
dynamically.

* `bigint.bfpp`: Definition of a few types representing bigger numbers than brainfuck normally supports, (16-, 32-bit).

## Error reference

There are around a dozen different error messages BFPP can produce. In the `errortrigs/`-directory, there are pieces of example code which trigger each
error.
