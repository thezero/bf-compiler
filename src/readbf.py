#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 23.10.2009

@author: The Zero
'''

import sys
if len(sys.argv)<2:
    print( 'Usage: %s <File> ' % sys.argv[0] )
    sys.exit(1)

try:
    stream = open(sys.argv[1], encoding = 'utf-8')
except Exception:
    print( 'Unable to open source file.')
    sys.exit(2)

try:
    run = False if sys.argv[2] == 'norun' else True
except Exception:
    run = True

lines = []
for line in stream:
    lines.append(line.strip(' \r\n\t'))
stream.close()
#'''
import compiler
cmp = compiler.Compiler()
source = cmp.compile("".join(lines))
f = open(sys.argv[1] + '.bfc', 'w')
f.write(source)
f.close()

if run:
    import pybf
    compiled = pybf.Pybf()
    compiled.run()
'''

import brainfuck
intr = brainfuck.Brainfuck("".join(lines), bits=16)
intr.chr()
'''
