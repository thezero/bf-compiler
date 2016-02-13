#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Created on 25.1.2010

@author: The Zero
'''

from tokens import ComplexOp, Data, In, Loop, Move, Out, Program, Reset
from langtemplate.c import C
from langtemplate.pyth import Pyth
from langtemplate.php import Php

'''
Generates Python code from Brainfuck.
Supports "compiled" bf code (microoptimizations)
'''
class Brainfuck2Python():
    '''
    Constructor

    @param source: brainfuck source code
    '''
    def __init__(self, source, bits = 8):
        # bf source code
        self.source = source
        # position of pointer to source code
        self.pos = 0
        # generated py source code parts "tokens"
        self.token = {'lines':[], 'loops':{}}
        self.headerToken = {'lines':[], 'loops':{}}
        self.footerToken = {'lines':[], 'loops':{}}
        # cycle stack
        self.stack = []
        # current token
        self.currentToken = self.token
        # current indentation for pretty-print
        self.indent = 0
        # previous op
        self.last = ''
        # static value
        self.staticValue = 0
        # max value
        self.bits = bits
        self.maxValue = 2**bits

        # program features
        self.features = {
            'move': False,
            'data': False,
            'dataop': False,
            'out': False,
            'cin': False,
            'ptr': False,
            'find': False,
            'tmp': False
        }

        self.chr()

        # destination file
        self.dst = open(self.template.filename, mode='w', encoding='utf-8')

        self.file(self.headerToken)
        self.file(self.currentToken)
        self.file(self.footerToken)

        self.dst.close()

    '''
    Processes next character
    '''
    def chr(self):
        c = self.get()
        program = Program()
        container = program
        prev = program.lastToken
        while None != c:
            if '>' == c:
                token = Move(1)
            elif '<' == c:
                token = Move(-1)
            elif '+' == c:
                token = Data(1)
            elif '-' == c:
                token = Data(-1)
            elif '.' == c:
                token = Out()
            elif '[' == c:
                token = Loop(container)
                token.setpos(self.pos)
                token.link(prev)
                prev = token.firstToken
                container.addToken(token)
                container = token
                token = None
            elif ']' == c:
                prev = container
                container = container.close()
                token = None
            elif ',' == c:
                token = In()
            elif 'x' == c:
                token = Data(self.getGroup())
            elif '_' == c:
                token = Data(-self.getGroup())
            elif '{' == c:
                token = Move(-self.getGroup())
            elif '}' == c:
                token = Move(self.getGroup())
            elif '0' == c:
                token = Reset()
            elif 'R' == c:
                token = Reset()
            elif 'm' == c:
                token = self.createComplexOp()

            if None != token:
                token.setpos(self.pos)
                container.addToken(token)
                token.link(prev)
                prev = token
            c = self.get()
            token = None

        if program != container:
            raise RuntimeError('Program ended in an unclosed loop')

        self.template = Pyth(self)
        #self.template = Php(self)
        #self.template = C(self)
        program.process(self)
        program.write(self)

        tempToken = self.currentToken
        self.currentToken = self.headerToken
        self.template.header()
        self.currentToken = tempToken

        self.currentToken = self.footerToken
        self.template.footer()
        self.currentToken = tempToken

    '''
    Returns next character of code. None at the end.
    '''
    def get(self):
        if self.pos < len(self.source):
            self.pos += 1
            return self.source[self.pos - 1]
        return None

    '''
    Appends nicely indented line to target source code
    '''
    def write(self, line):
        self.currentToken['lines'].append(('\t' * self.indent) + line.lstrip())

    '''
    Puts generated tokens into file
    '''
    def file(self, token):
        line = ''
        for line in token['lines']:
            if None != line:
                self.dst.write(line + '\n')

        if 'class Pybf():' != line:
            # hack, we skipped header
            self.dst.write('\n')

        for loop in token['loops'].values():
            self.file(loop)

    '''
    Returns the size of current group (group inc, move, etc.)
    '''
    def getGroup(self):
        end = self.source.index(';', self.pos)
        tmp = self.pos
        self.pos = end + 1
        return int(self.source[tmp:end])

    def createComplexOp(self):
        token = ComplexOp()

        i = self.getGroup()
        while 0 != i:
            token.addReset(i)
            i = self.getGroup()

        i = self.getGroup()
        while 0 != i:
            x = self.getGroup()
            token.addMove(i, x)
            i = self.getGroup()

        return token
