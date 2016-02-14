'''
Created on 29.11.2010

@author: The Zero
'''

class Php():
    filename = 'bfphp.php'

    def __init__(self, code):
        self.code = code

    def getPtr(self, ptr):
        if None == ptr:
            self.code.features['ptr'] = True
        return '$this->ptr' if None == ptr else str(ptr)

    def initMem(self, size):
        self.code.write('$this->data = array_fill(0, ' + str(size) + ', 0);')

    def find(self):
        self.code.features['ptr'] = True
        self.code.features['find'] = True
        self.code.write('$this->find();')

    def data(self, value):
        self.code.features['dataop'] = True
        if isinstance(value, str):
            value = value.replace('tmp', '$tmp')
            if '-' == value[0]:
                self.code.write('$this->dec(' + value[1:] + ');')
            else:
                self.code.write('$this->inc(' + value + ');')
        elif value == 1:
            self.code.write('$this->inc();')
        elif value == -1:
            self.code.write('$this->dec();')
        elif value > 0:
            self.code.write('$this->inc(' + str(value) + ');')
        else:
            self.code.write('$this->dec(' + str(-value) + ');')

    def staticData(self, value, ptr = None):
        self.code.write('$this->data[' + self.getPtr(ptr) + '] = ' + str(value) + ';')

    def tmpData(self, mul, ptr = None):
        num = '$tmp'
        if (None != mul) and (1 != mul) and (-1 != mul):
            if mul > 0:
                num += ' * ' + str(mul)
            else:
                num += ' * ' + str(-mul)

        if None == ptr:
            if mul > 0:
                self.code.write('$this->inc(' + num + ');')
            else:
                self.code.write('$this->dec(' + num + ');')
        else:
            strPos = '$this->data[' + self.getPtr(ptr) + ']'
            if mul == None:
                self.code.write(strPos + ' = $tmp')
            elif mul > 0:
                self.code.write(strPos + ' = (' + strPos + ' + ' + num + ') % $this->limit;')
            else:
                self.code.write(strPos + ' = (' + strPos + ' - ' + num + ') % $this->limit;')

    def move(self, offset):
        self.code.features['move'] = True
        if offset > 0:
            self.code.write('$this->rgt(' + str(offset) + ');')
        else:
            self.code.write('$this->lft(' + str(-offset) + ');')

    def staticMove(self, ptr):
        self.code.features['ptr'] = True
        self.code.write('$this->ptr = ' + str(ptr) + ';')

    def cin(self):
        self.code.features['cin'] = True
        self.code.write('$this->cin();')

    def tmp(self, change, ptr = None):
        self.code.features['data'] = True
        ptr = self.getPtr(ptr)
        if change < 0:
            self.code.write('$tmp = $this->data[' + ptr + '] - ' + str(-change) + ';')
        elif change > 0:
            self.code.write('$tmp = $this->data[' + ptr + '] + ' + str(change) + ';')
        else:
            self.code.write('$tmp = $this->data[' + ptr + '];')

    def out(self, value = None, pos = None):
        self.code.features['out'] = True
        if None != value:
            self.code.write('$this->out(' + str(value) + ');')
        elif None != pos:
            self.code.features['ptr'] = True
            self.code.features['data'] = True
            self.code.write('$this->out(self.data[' + str(pos) + ']);')
        else:
            self.code.features['data'] = True
            self.code.features['ptr'] = True
            self.code.write('$this->out();')

    def multiOut(self, chars):
        out = '"'
        for char in chars:
            if 10 == char or 13 == char:
                out += '\\n'
            elif char < 32:
                out += '" + chr(' + str(char) + ') + "'
            elif 92 == char:
                out += '\\\\'
            else:
                printed = chr(char)
                if '"' == printed:
                    printed = '\\"'
                out += printed
        out += '"'
        self.code.write('echo ' + out + ';')

    def startProgram(self):
        self.code.indent = 1
        self.code.write('    public function run() {')
        self.code.indent = 2
        return None

    def endProgram(self, context):
        self.code.indent = 1
        self.code.write('    }')
        self.code.indent = 0

    def callLoop(self, pos):
        self.code.write('$this->loop' + str(pos) + '();')

    def startLoop(self, pos, ptr):
        indent = self.code.indent
        ptr = self.getPtr(ptr)
        self.code.indent = 1
        self.code.write('     private function loop' + str(pos) + '() {')
        self.code.indent = 2
        self.code.write('        while ($this->data[' + ptr + ']) {')
        self.code.indent = 3
        return indent

    def endLoop(self, context):
        self.code.indent -= 1
        self.code.write('        }')
        self.code.indent -= 1
        self.code.write('    }')
        self.code.indent = context

    def startInlineIf(self, ptr):
        ptr = self.getPtr(ptr)
        self.code.write('if ($this->data[' + ptr + ']) {')
        self.code.indent += 1
        return None

    def endInlineIf(self, context):
        self.code.indent -= 1
        self.code.write('}')

    def callIf(self, pos):
        self.code.write('$this->if' + str(pos) + '();')

    def startIf(self, pos, ptr):
        indent = self.code.indent
        self.code.indent = 1
        self.code.write('     private function if' + str(pos) + '() {')
        self.code.indent = 2
        self.startInlineIf(ptr)
        return indent

    def endIf(self, context):
        self.endInlineIf(None)
        self.code.indent -= 1
        self.code.write('    }')
        self.code.indent = context

    def debugLoop(self, loop):
        self.code.write('// loop is stable: ' + str(loop.stable) + ', simple: ' + str(loop.simple))

    def debugToken(self, token):
        self.code.write('// token ' + str(token.__class__.__name__) + ' static pos:' + str(token.staticPos) + ', value: ' + str(token.staticValue) + ', pos: ' + str(token.pos))


    '''
    Generates file header, class and basic methods
    '''
    def header(self):
        self.code.write('#!/usr/bin/php')
        self.code.write('<?php')
        self.code.write('')

        self.code.write('class Bfphp')
        self.code.write('{')
        self.code.indent += 1

        if True not in self.code.features.values():
            return

        if self.code.features['data'] or self.code.features['dataop'] or self.code.features['move'] or self.code.features['cin']:
            self.code.write('    private $data = array(0);')
        if self.code.features['ptr'] or self.code.features['dataop'] or self.code.features['move']:
            self.code.write('    private $ptr = 0;')
        if self.code.features['out']:
            self.code.write('    private $lastout = 0;')
        if self.code.features['data'] or self.code.features['dataop']:
            self.code.write('    private $limit;')
        self.code.write('    public function __construct($bits = ' + str(self.code.bits) +') {')
        self.code.indent += 1
        if self.code.features['data'] or self.code.features['dataop']:
            self.code.write('        $this->limit = pow(2, $bits);')
        self.code.indent -= 1
        self.code.write('    }')

        if self.code.features['dataop']:
            self.code.write('')
            self.code.write('    private function inc($num=1) {')
            self.code.indent += 1
            self.code.write('        $this->data[$this->ptr] += $num;')
            self.code.write('        if ($this->data[$this->ptr] >= $this->limit) {')
            self.code.indent += 1
            self.code.write('            $this->data[$this->ptr] = $this->data[$this->ptr] % $this->limit;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.write('')

            self.code.write('     private function dec($num=1) {')
            self.code.indent += 1
            self.code.write('        $this->data[$this->ptr] -= $num;')
            self.code.write('        if ($this->data[$this->ptr] < 0) {')
            self.code.indent += 1
            self.code.write('            $this->data[$this->ptr] = $this->data[$this->ptr] % $this->limit;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.write('')

        if self.code.features['move']:
            self.code.write('')
            self.code.write('     private function rgt($num=1) {')
            self.code.indent += 1
            self.code.write('        $this->ptr += $num;')
            self.code.write('        while ($this->ptr >= count($this->data)) {')
            self.code.indent += 1
            self.code.write('            $this->data[] = 0;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.write('')

            self.code.write('')
            self.code.write('     private function lft($num=1) {')
            self.code.indent += 1
            self.code.write('        $this->ptr -= $num;')
            self.code.write('        if ($this->ptr < 0) {')
            self.code.indent += 1
            self.code.write('            $this->ptr = 0;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write('    }')
            self.code.write('')

        if self.code.features['out'] or self.code.features['cin']:
            self.code.write('')
            self.code.write('     private function out($char = null) {')
            self.code.indent += 1
            self.code.write('        if (null === $char) { $char = $this->data[$this->ptr]; }')
            self.code.write('        if (13 == $char) {')
            self.code.indent += 1
            self.code.write('            if (10 != $this->lastout) {')
            self.code.indent += 1
            self.code.write('                 echo "\\n";')
            self.code.write('                 $this->lastout = $char;')
            self.code.indent -= 1
            self.code.write('            }')
            self.code.indent -= 1
            self.code.write('        } elseif (10 == $char) {')
            self.code.indent += 1
            self.code.write('            if (13 != $this->lastout) {')
            self.code.indent += 1
            self.code.write('                 echo "\\n";')
            self.code.write('                 $this->lastout = $char;')
            self.code.indent -= 1
            self.code.write('            }')
            self.code.indent -= 1
            self.code.write('        } else {')
            self.code.indent += 1
            self.code.write('            echo chr($char);')
            self.code.write('            $this->lastout = $char;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write('    }')

        if self.code.features['cin']:
            raise NotImplementedError()

        if self.code.features['find']:
            self.code.write('')
            self.code.write('     private function find() {')
            self.code.indent += 1
            self.code.write('        $ptr = $this->ptr;')
            self.code.write('        $keys = array_keys($this->data, 0);')
            self.code.write('        $key = array_shift($keys);')
            self.code.write('        while ($key <= $this->ptr && $key !== null) {')
            self.code.indent += 1
            self.code.write('            $key = array_shift($keys);')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.write('        if ($key === null) {')
            self.code.indent += 1
            self.code.write('            $this->ptr = count($this->data);')
            self.code.write('            $this->data[] = 0;')
            self.code.indent -= 1
            self.code.write('        } else {')
            self.code.indent += 1
            self.code.write('            $this->ptr = $key;')
            self.code.indent -= 1
            self.code.write('        }')
            self.code.indent -= 1
            self.code.write('    }')

    '''
    Generates file footer for running script directly
    '''
    def footer(self):
        self.code.indent = 0
        self.code.write('}')
        self.code.write('')
        self.code.write('$bf = new Bfphp();')
        self.code.write('$bf->run();')
