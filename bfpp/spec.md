This preproccessor is backwards compatible with brainfuck, and has a few extra features added to it.
===

**Named memory locations:**

`(? location1 location2 ... >location_pointed_to ... location_n)` declares all named locations.

`(!location)` goes to that location.

Named memory locations are preserved after loops that keep the pointer in the same place before and
after.

Example code:

```
/* Print the letter A */
(? >number temp)
(!temp) ++++ ++++
[
    (!number) ++++ ++++
    (!temp) -
]
(!number) + .
```

**Repetition:**

Repeat a command by putting a number after it. To repeat a group of commands, put them inside
parentheses.

Example code:

```
/* Print the alphabet */
+64 (+.) 26
```

**Macros:**

Macros can be defined in the following way: `def macroname (? arg1 ... >arg_pointed_to ... argN) {
body }`. They can later be invoked like this: `inv macroname (arg1 ... argN)`.

Example code:
```
/* Copy things around */
def copy(? >source dest tmp) {
    [
        (!dest) +
        (!tmp) +
        (!source) -
    ]
    (!tmp) [
        (!source) +
        (!tmp) -
    ]
}

(?>tmp a b c d)

(!a) +5
(!b) +7
inv copy(a d tmp)
inv copy(b c tmp)
```

**Predefined macros:**

`add0(n tmp)`...`add255(n tmp)`: increase `n` by a certain number. `tmp` is assumed to be `0`, and
will be `0` after. Uses the following construct: `(!tmp) +X [(!n) +Y (!tmp) -Z] (!n) +K` for some
numbers X, Y, Z, K.

**Prepreprocessor:**
The `#include filename.bfpp` copies the code of another file into that place.
