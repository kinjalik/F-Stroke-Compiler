# F-Stroke Language Compiler
This is a solution for ![an assignment](assignments.pdf) from the 2nd qualifying stage of the NTI Contest in Software Engineering for Financial Technology.
## What is F-Stroke?
> **F-Stroke** is programming language, which supports ![functional programming](https://en.wikipedia.org/wiki/Functional_programming). Being simplified and modified version of Lisp language, F-Stroke takes base syntax and semantics from it
> - Description of assignment
## Usage
```
usage: main.py [-h] [-o O] [--hex-size HEX_SIZE] input

positional arguments:
  input                File to input with F-Stroke code

optional arguments:
  -h, --help           show this help message and exit
  -o O                 File to output with Ethereum Byte Code
  --hex-size HEX_SIZE  Size of hex numbers in bytes (max and default 32)

```

### Examples
```
python3 main.py input.fst
```
```
python3 main.py input.fst -o out.ebc
```
## Plans and perspectives
- Make automated tests of every new version of compiler using GitHub Actions of GitLab CI/CD
- Make automated assembly of compiler into one `.py` file and prepare it to sending on Stepik (where judge system placed)
