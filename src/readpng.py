#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 23.10.2009

@author: The Zero
'''

import sys
if len(sys.argv)<3:
    print( 'Usage: %s <loller|copter> <File> q?' % sys.argv[0] )
    sys.exit(1)

from pngreader import Png
from image2bf import Image2Bf
if ('loller' != sys.argv[1] and 'copter' != sys.argv[1]):
    print( 'Usage: %s <loller|copter> <File> q?' % sys.argv[0] )
    sys.exit(2)

png = Png(sys.argv[2])

# quiet move for simple programs
# add " q" after standard command
verbose = True
if (len(sys.argv) > 3 and 'q' == sys.argv[3]):
    verbose = False

if (True == verbose):
    print ('reading image')
png.read()

if (True == verbose):
    print ('converting to brainfuck')
convert = Image2Bf()
plainbf = ''
if ('loller' == sys.argv[1]):
    plainbf = convert.loller(png.png['image'])
else:
    plainbf = convert.copter(png.png['image'])
png = None
f = open(sys.argv[2] + '.bf', 'w')
f.write(plainbf)
f.close()

if (True == verbose):
    print ('compiling')
import compiler
cmp = compiler.Compiler()
source = cmp.compile(plainbf)
f = open(sys.argv[2] + '.bfc', 'w')
f.write(source)
f.close()

if (True == verbose):
    print ('running')
    print ('')

import pybf
compiled = pybf.Pybf()
compiled.run()
