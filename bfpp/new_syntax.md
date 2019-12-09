## Variables

### Declaration:

```
declare (
    datatype varname,
    ...
    ,
) at varname
```

### Variable references

```
to varname
```

### Example

```
/* Print the letter A */
declare (cell number, cell temp) at number

to temp ++++ ++++
[
    to number ++++ ++++
    to temp -
]
to number + .
```

## Macros

### Declaration

```
def macroname(datatype varname, ...) at varname {
    ...
}
```

### Usage

run macroname(varname, ...)

## Preprocessor

```
#include <xyz.bfpp>
```

## Loops

### Stable loops

As normal in brainfuck

```
[ code ]
```

### Unstable loops

```
unstable [ code ]
```

## Types

```

type chpair (
    cell ch1,
    cell ch2,
)


```