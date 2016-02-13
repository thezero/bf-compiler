# bf-compiler

This is simply yet another optimizing Brainfuck compiler written in Python.
It features a lot of naïve optimizations and messy code :)

## Origin

The interpreter part was done for Python college class at
[FIT ČVUT] (http://fit.cvut.cz) by [Jiří Znamenáček] (http://ookami.cz)

The compile/optimize part was created whenever I was feeling bored at home
with sometimes few years inbetween, hence the duplicated and messy code :)

## Features

### Supported Brainfuck variants

* regular BF code, wrapped memory (by default 8 bit, can be changed in code)
* brainloller and braincopter (BF embedded into image file) - only uncompressed
  PNG supported
* passes most of
  [compiler tests] (http://www.hevanet.com/cristofd/brainfuck/tests.b)

### Language templates

* Python (default, input on Windows) (slow, unlimited memory)
* C (full support) (fastest when compiled, 30k cells as per original spec)
* PHP (no input support) (PHP 5 slower than Python 3.5, PHP 7 faster)

### Optimizations

* Merging of consecutive operations
* Move, multiply and reset transformed into single operation
* Dead code elimination
* Value and pointer tracking when code is not too complicated
* Can simplify
  [Hello world!] (http://esoteric.sange.fi/brainfuck/bf-source/prog/) programs
  into `print ("Hello world!")`

## Usage

Always creates `pybf.py` file right inside `src` dir, so make sure it's
writable.

standard brainfuck files:
> python readbf.py /path/to/file

brainloller:
> python readpng.py loller /path/to/file

braincopter:
> python readpng.py copter /path/to/file

silent png (no progress info):
> python readpng.py loller|copter /path/to/file q

run last compiled file:
> python pybf.py

## Todo (in case I'm bored again)

* Feature parity on all language templates:
  - universal input in Python
  - input in PHP
  - unlimited memory in C
* Code cleanup
* More optimizations if I find any

## Inspiration
* [esolangs] (http://esolangs.org/wiki/Category:Brainfuck)
* [esotope-bfc] (http://code.google.com/p/esotope-bfc/) probably the most
  optimizing brainfuck compiler I found, also in Python
* [Brainfuck Archive] (http://esoteric.sange.fi/brainfuck/)
