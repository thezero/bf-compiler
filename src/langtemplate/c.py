'''
Created on 29.11.2010

@author: The Zero
'''

class C():
    filename = 'bfc.c'

    def __init__(self, code):
        self.code = code
        self.functionRegister = []

    def getPtr(self, ptr):
        if None == ptr:
            self.code.features['ptr'] = True
        return 'ptr' if None == ptr else str(ptr)

    def initMem(self, size):
        pass

    def find(self):
        self.code.features['ptr'] = True
        self.code.features['find'] = True
        self.code.write('find();')

    def data(self, value):
        self.code.features['dataop'] = True
        if isinstance(value, str):
            if '-' == value[0]:
                self.code.write('data[ptr] -= ' + value[1:] + ';')
            else:
                self.code.write('data[ptr] += ' + value + ';')
        elif value == 1:
            self.code.write('++data[ptr];')
        elif value == -1:
            self.code.write('--data[ptr];')
        elif value > 0:
            self.code.write('data[ptr] += ' + str(value) + ';')
        else:
            self.code.write('data[ptr] -= ' + str(-value) + ';')

    def staticData(self, value, ptr = None):
        self.code.write('data[' + self.getPtr(ptr) + '] = ' + str(value) + ';')

    def tmpData(self, mul, ptr = None):
        num = 'tmp'
        if (None != mul) and (1 != mul) and (-1 != mul):
            if mul > 0:
                num += ' * ' + str(mul)
            else:
                num += ' * ' + str(-mul)

        if None == ptr:
            if mul > 0:
                self.code.write('data[ptr] += ' + num + ';')
            else:
                self.code.write('data[ptr] -= ' + num + ';')
        else:
            strPos = 'data[' + self.getPtr(ptr) + ']'
            if mul == None:
                self.code.write(strPos + ' = tmp;')
            elif mul > 0:
                self.code.write(strPos + ' += ' + num + ';')
            else:
                self.code.write(strPos + ' -= ' + num + ';')

    def move(self, offset):
        self.code.features['move'] = True
        if offset > 0:
            self.code.write('rgt(' + str(offset) + ');')
        else:
            self.code.write('lft(' + str(-offset) + ');')

    def staticMove(self, ptr):
        self.code.features['ptr'] = True
        self.code.write('ptr = ' + str(ptr) + ';')

    def cin(self):
        self.code.features['cin'] = True
        self.code.write('cin();')

    def tmp(self, change, ptr = None):
        self.code.features['data'] = True
        self.code.features['tmp'] = True
        ptr = self.getPtr(ptr)
        if change < 0:
            self.code.write('tmp = data[' + ptr + '] - ' + str(-change) + ';')
        elif change > 0:
            self.code.write('tmp = data[' + ptr + '] + ' + str(change) + ';')
        else:
            self.code.write('tmp = data[' + ptr + ']' + ';')

    def out(self, value = None, pos = None):
        self.code.features['out'] = True
        if None != value:
            self.code.write('out(' + str(value) + ');')
        elif None != pos:
            self.code.features['ptr'] = True
            self.code.features['data'] = True
            self.code.write('out(data[' + str(pos) + ']);')
        else:
            self.code.features['data'] = True
            self.code.features['ptr'] = True
            self.code.write('out(data[ptr]);')

    def multiOut(self, chars):
        out = '"'
        params = ''
        for char in chars:
            if 10 == char or 13 == char:
                out += '\\n'
            elif char < 32:
                out += '%c'
                params += ', ' + str(char)
            else:
                printed = chr(char)
                if '"' == printed:
                    printed = '\\"'
                out += printed
        out += '"'
        self.code.write('printf(' + out + params + ');')

    def startProgram(self):
        self.code.indent = 0
        self.code.write('int main() {')
        self.code.indent += 1
        if self.code.features['data']:
            self.code.write('for (int i=0; i<30000; i++) {')
            self.code.indent += 1
            self.code.write('    data[i] = 0;')
            self.code.indent -= 1
            self.code.write('}')
        return None

    def endProgram(self, context):
        self.code.write('return 0;')
        self.code.indent = 0
        self.code.write('}')

    def callLoop(self, pos):
        self.code.write('loop' + str(pos) + '();')

    def startLoop(self, pos, ptr):
        indent = self.code.indent
        ptr = self.getPtr(ptr)
        self.functionRegister.append('void loop' + str(pos) + '()')
        self.code.indent = 0
        self.code.write('void loop' + str(pos) + '() {')
        self.code.indent = 1
        self.code.write('    while (data[' + ptr + ']) {')
        self.code.indent = 2
        return indent

    def endLoop(self, context):
        self.code.indent = 1
        self.code.write('}')
        self.code.indent = 0
        self.code.write('}')
        self.code.indent = context

    def startInlineIf(self, ptr):
        ptr = self.getPtr(ptr)
        self.code.write('if (data[' + ptr + ']) {')
        self.code.indent += 1
        return None

    def endInlineIf(self, context):
        self.code.indent -= 1
        self.code.write('}')

    def callIf(self, pos):
        self.code.write('if' + str(pos) + '();')

    def startIf(self, pos, ptr):
        indent = self.code.indent
        self.functionRegister.append('void if' + str(pos) + '()')
        self.code.indent = 0
        self.code.write('void if' + str(pos) + '() {')
        self.code.indent = 1
        self.startInlineIf(ptr)
        return indent

    def endIf(self, context):
        self.endInlineIf(None)
        self.code.indent = 0
        self.code.write('}')
        self.code.indent = context

    def debugLoop(self, loop):
        self.code.write('// loop is stable: ' + str(loop.stable) + ', simple: ' + str(loop.simple))

    def debugToken(self, token):
        self.code.write('// token ' + str(token.__class__.__name__) + ' static pos:' + str(token.staticPos) + ', value: ' + str(token.staticValue) + ', pos: ' + str(token.pos))


    '''
    Generates file header, class and basic methods
    '''
    def header(self):
        self.code.write('#include <stdio.h>')
        if self.code.features['cin']:
            self.code.write('#include <conio.h>')

        if True not in self.code.features.values():
            return

        if self.code.features['data'] or self.code.features['dataop'] or self.code.features['move'] or self.code.features['cin']:
            self.code.write('unsigned short data[30000];')
        if self.code.features['ptr'] or self.code.features['dataop'] or self.code.features['move']:
            self.code.write('int ptr = 0;')
        if self.code.features['out']:
            self.code.write('char lastout = 0;')
        if self.code.features['tmp']:
            self.code.write('char tmp;')
        self.code.indent -= 1

        if self.code.features['move']:
            self.code.write('')
            self.code.indent = 0
            self.code.write('void rgt(int move) {')
            self.code.indent += 1
            self.code.write('    ptr += move;')
            # ignore 30k overflow for now
            self.code.indent -= 1
            self.code.write('}')

            # snažíme se být co nejmilejší a posuny do mínusu ignorujeme
            self.code.write('')
            self.code.indent = 0
            self.code.write('void lft(int move) {')
            self.code.indent += 1
            self.code.write('    ptr -= move;')
            self.code.write('    if (ptr < 0) {')
            self.code.indent += 1
            self.code.write('        ptr = 0;')
            self.code.indent -= 1
            self.code.write('}')
            self.code.indent -= 1
            self.code.write('}')

        if self.code.features['out'] or self.code.features['cin']:
            self.code.write('')
            self.code.write('void out(char val) {')
            self.code.indent += 1
            self.code.write("    if ('\\n' == val) {")
            self.code.indent += 1
            self.code.write("        if ('\\r' != lastout) {")
            self.code.indent += 1
            self.code.write('            printf ("\\n");')
            self.code.write('            lastout = val;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write("    } else if ('\\r' == val) {")
            self.code.indent += 1
            self.code.write("        if ('\\n' != lastout) {")
            self.code.indent += 1
            self.code.write('            printf ("\\n");')
            self.code.write('            lastout = val;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write("    } else {")
            self.code.indent += 1
            self.code.write('        printf ("%c", val);')
            self.code.write('        lastout = val;')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.indent -= 1
            self.code.write('}')

        if self.code.features['cin']:
            # currently windows only
            self.code.write('')
            self.code.indent = 0
            self.code.write('void cin() {')
            self.code.indent += 1
            self.code.write('    char val;')
            self.code.write('    val = getch();')
            self.code.write("    if (val == '\\x1A') {")
            self.code.indent += 1
            self.code.write('            return;')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.write("    if ('\\r' == val) { val = '\\n'; }")
            self.code.write('    data[ptr] = val;')
            self.code.write('    out(val);')
            self.code.indent -= 1
            self.code.write('}')

        if self.code.features['find']:
            self.code.write('')
            self.code.indent = 0
            self.code.write('void find() {')
            self.code.indent += 1
            self.code.write('    while (data[ptr]) {')
            self.code.indent += 1
            self.code.write('        ++ptr;')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.indent -= 1
            self.code.write('}')

        self.code.indent = 0;
        for i in self.functionRegister:
            self.code.write(i + ';')

    '''
    Generates file footer for running script directly
    '''
    def footer(self):
        pass
