'''
Created on 29.11.2010

@author: The Zero
'''

class Pyth():
    filename = 'pybf.py'

    def __init__(self, code):
        self.code = code

    def getPtr(self, ptr):
        if None == ptr:
            self.code.features['ptr'] = True
        return 'self.ptr' if None == ptr else str(ptr)

    def initMem(self, size):
        self.code.write('self.data = [0 for i in range(0, ' + str(size) + ')]')

    def find(self):
        self.code.features['ptr'] = True
        self.code.features['find'] = True
        self.code.write('self.find()')

    def data(self, value):
        self.code.features['dataop'] = True
        if isinstance(value, str):
            if '-' == value[0]:
                self.code.write('self.dec(' + value[1:] + ')')
            else:
                self.code.write('self.inc(' + value + ')')
        elif value == 1:
            self.code.write('self.inc()')
        elif value == -1:
            self.code.write('self.dec()')
        elif value > 0:
            self.code.write('self.inc(' + str(value) + ')')
        else:
            self.code.write('self.dec(' + str(-value) + ')')

    def staticData(self, value, ptr = None):
        self.code.write('self.data[' + self.getPtr(ptr) + '] = ' + str(value))

    def tmpData(self, mul, ptr = None):
        num = 'tmp'
        if (None != mul) and (1 != mul) and (-1 != mul):
            if mul > 0:
                num += ' * ' + str(mul)
            else:
                num += ' * ' + str(-mul)

        if None == ptr:
            if mul > 0:
                self.code.write('self.inc(' + num + ')')
            else:
                self.code.write('self.dec(' + num + ')')
        else:
            strPos = 'self.data[' + self.getPtr(ptr) + ']'
            if mul == None:
                self.code.write(strPos + ' = tmp')
            elif mul > 0:
                self.code.write(strPos + ' = (' + strPos + ' + ' + num + ') % self.limit')
            else:
                self.code.write(strPos + ' = (' + strPos + ' - ' + num + ') % self.limit')

    def move(self, offset):
        self.code.features['move'] = True
        if offset > 0:
            self.code.write('self.rgt(' + str(offset) + ')')
        else:
            self.code.write('self.lft(' + str(-offset) + ')')

    def staticMove(self, ptr):
        self.code.features['ptr'] = True
        self.code.write('self.ptr = ' + str(ptr))

    def cin(self):
        self.code.features['cin'] = True
        self.code.write('self.cin()')

    def tmp(self, change, ptr = None):
        self.code.features['data'] = True
        ptr = self.getPtr(ptr)
        if change < 0:
            self.code.write('tmp = self.data[' + ptr + '] - ' + str(-change))
        elif change > 0:
            self.code.write('tmp = self.data[' + ptr + '] + ' + str(change))
        else:
            self.code.write('tmp = self.data[' + ptr + ']')

    def out(self, value = None, pos = None):
        self.code.features['out'] = True
        if None != value:
            self.code.write('self.out(' + str(value) + ')')
        elif None != pos:
            self.code.features['ptr'] = True
            self.code.features['data'] = True
            self.code.write('self.out(self.data[' + str(pos) + '])')
        else:
            self.code.features['data'] = True
            self.code.features['ptr'] = True
            self.code.write('self.out()')

    def multiOut(self, chars):
        out = '"'
        for char in chars:
            if 10 == char or 13 == char:
                out += '\\n'
            elif char < 32:
                out += '" + chr(' + str(char) + ') + "'
            else:
                out += chr(char)
        out += '"'
        if 10 == chars[-1] or 13 == chars[-1]:
            out = out[:-3] + '"'
            self.code.write('print (' + out + ')')
        else:
            self.code.write('print (' + out + ', end=\'\')')

    def startProgram(self):
        self.code.indent = 1
        self.code.write('    def run(self):')
        self.code.indent = 2
        return None

    def endProgram(self, context):
        self.code.indent = 0

    def callLoop(self, pos):
        self.code.write('self.loop' + str(pos) + '()')

    def startLoop(self, pos, ptr):
        indent = self.code.indent
        ptr = self.getPtr(ptr)
        self.code.indent = 1
        self.code.write('    def loop' + str(pos) + '(self):')
        self.code.indent = 2
        self.code.write('        while 0 != self.data[' + ptr + ']:')
        self.code.indent = 3
        return indent

    def endLoop(self, context):
        self.code.indent = context

    def startInlineIf(self, ptr):
        ptr = self.getPtr(ptr)
        self.code.write('if 0 != self.data[' + ptr + ']:')
        self.code.indent += 1
        return None

    def endInlineIf(self, context):
        self.code.indent -= 1

    def callIf(self, pos):
        self.code.write('self.if' + str(pos) + '()')

    def startIf(self, pos, ptr):
        indent = self.code.indent
        self.code.indent = 1
        self.code.write('    def if' + str(pos) + '(self):')
        self.code.indent = 2
        self.startInlineIf(ptr)
        return indent

    def endIf(self, context):
        self.endInlineIf(None)
        self.code.indent = context

    def debugLoop(self, loop):
        self.code.write('# loop is stable: ' + str(loop.stable) + ', simple: ' + str(loop.simple) + ', within: ' + str(loop.isChangeWithinBoundary()))
        self.code.write('# changes: max %d min %d off %d ' % (loop.changeWithinBoundaryMax, loop.changeWithinBoundaryMin, loop.changeWithinBoundaryOff, ))

    def debugToken(self, token):
        #pass
        self.code.write('# token ' + str(token.__class__.__name__) + ' static pos:' + str(token.staticPos) + ', value: ' + str(token.staticValue) + ', pos: ' + str(token.pos))


    '''
    Generates file header, class and basic methods
    '''
    def header(self):
        self.code.write('#!/usr/bin/env python')
        self.code.write('# -*- coding: utf-8 -*-')
        self.code.write('')

        self.code.write('class Pybf():')
        self.code.indent += 1

        if True not in self.code.features.values():
            return

        self.code.write('    def __init__(self, bits = ' + str(self.code.bits) +'):')
        self.code.indent += 1
        if self.code.features['data'] or self.code.features['dataop'] or self.code.features['move'] or self.code.features['cin']:
            self.code.write('        self.data = [0]')
        if self.code.features['ptr'] or self.code.features['dataop'] or self.code.features['move']:
            self.code.write('        self.ptr = 0')
        if self.code.features['out']:
            self.code.write('        self.lastout = 0')
        if self.code.features['data'] or self.code.features['dataop']:
            self.code.write('        self.limit = 2**bits')
        self.code.indent -= 1

        if self.code.features['dataop']:
            self.code.write('')
            self.code.write('    def inc(self, num=1):')
            self.code.indent += 1
            self.code.write('        self.data[self.ptr] += num')
            self.code.write('        if self.data[self.ptr] >= self.limit:')
            self.code.indent += 1
            self.code.write('            self.data[self.ptr] = self.data[self.ptr] % self.limit')
            self.code.indent -= 2
            self.code.write('')

            self.code.write('    def dec(self, num=1):')
            self.code.indent += 1
            self.code.write('        self.data[self.ptr] -= num')
            self.code.write('        if self.data[self.ptr] < 0:')
            self.code.indent += 1
            self.code.write('            self.data[self.ptr] = self.data[self.ptr] % self.limit')
            self.code.indent -= 2

        if self.code.features['move']:
            self.code.write('')
            self.code.write('    def rgt(self, num=1):')
            self.code.indent += 1
            self.code.write('        self.ptr += num')
            self.code.write('        while self.ptr >= len(self.data):')
            self.code.indent += 1
            self.code.write('            self.data.append(0)')
            self.code.indent -= 2

            # snažíme se být co nejmilejší a posuny do mínusu ignorujeme
            self.code.write('')
            self.code.write('    def lft(self, num=1):')
            self.code.indent += 1
            self.code.write('        self.ptr -= num')
            self.code.write('        if (self.ptr < 0):')
            self.code.indent += 1
            self.code.write('            self.ptr = 0')
            self.code.indent -= 2

        if self.code.features['out'] or self.code.features['cin']:
            self.code.write('')
            self.code.write('    def out(self, char = None):')
            self.code.indent += 1
            self.code.write('        if None == char: char = self.data[self.ptr]')
            self.code.write('        if 13 == char:')
            self.code.indent += 1
            self.code.write('            if 10 != self.lastout:')
            self.code.indent += 1
            self.code.write('                 print ("")')
            self.code.write('                 self.lastout = char')
            self.code.indent -= 2
            self.code.write('        elif 10 == char:')
            self.code.indent += 1
            self.code.write('            if 13 != self.lastout:')
            self.code.indent += 1
            self.code.write('                 print ("")')
            self.code.write('                 self.lastout = char')
            self.code.indent -= 2
            self.code.write('        else:')
            self.code.indent += 1
            self.code.write('            print ("%c" % char, end=\'\')')
            self.code.write('            self.lastout = char')
            self.code.indent -= 2

        if self.code.features['cin']:
            # currently windows only
            self.code.write('')
            self.code.write('    def cin(self):')
            self.code.indent += 1
            self.code.write('        import sys')
            self.code.write('        import msvcrt')
            # immediate flush needed - buffering does not work well with some
            # programs
            self.code.write('        sys.stdout.flush()')
            self.code.write('        chr = msvcrt.getch()')
            self.code.write('        while chr in b\'\\x00\\xe0\':')
            self.code.indent += 1
            self.code.write('            chr = msvcrt.getch()')
            self.code.indent -= 1
            self.code.write('        if b\'\\x1A\' == chr:')
            self.code.indent += 1
            self.code.write('            return')
            self.code.indent -= 1
            self.code.write('        val = ord(chr)')
            self.code.write('        if 10 == val or 13 == val: self.data[self.ptr] = 10')
            self.code.write('        if val >= 32: self.data[self.ptr] = val')
            self.code.write('        self.out()')
            self.code.indent -= 1

        if self.code.features['find']:
            self.code.write('')
            self.code.write('    def find(self):')
            self.code.indent += 1
            self.code.write('        try:')
            self.code.indent += 1
            self.code.write('            self.ptr = self.data.index(0, self.ptr)')
            self.code.indent -= 1
            self.code.write('        except ValueError:')
            self.code.indent += 1
            self.code.write('            self.ptr = len(self.data)')
            self.code.write('            self.data.append(0)')
            self.code.indent -= 2

    '''
    Generates file footer for running script directly
    '''
    def footer(self):
        self.code.indent = 0
        self.code.write('if __name__ == "__main__":')
        self.code.indent = 1
        self.code.write('Pybf().run()')
