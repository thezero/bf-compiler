'''
Created on 6.11.2009

@author: The Zero
'''

import re
import b2p

'''
Brainfuck code compiler (microoptimization)
'''
class Compiler():
    '''
    Constructor
    '''
    def __init__(self):
        pass

    '''
    Compiles source code and generates python version

    @param source: Brainfuck source code
    @return: compiled source code
    '''
    def compile(self, source):
        self.source = source
        self.clean()

        self.packReset()
        self.anyPack()
        self.packInc()
        self.packDec()
        # handled in anypack
        # self.packOneIf()
        self.packShift()
        # no need for static hints - compiler detects them using AST
        #self.staticSet()

        b2p.Brainfuck2Python(self.source);

        return self.source

    '''
    Removes all non-brainfuck characters which may interfere with
    custom optimized commands
    '''
    def clean(self):
        p = re.compile('[^><+.\[\],\-]+', re.IGNORECASE)
        self.source = p.sub("", self.source)

        # empty loop - for compliance with brainfuck testing programs
        self.source = self.source.replace('[]', '')

    '''
    Packs increments - adds 4 instead of adding 1 four times
    '''
    def packInc(self):
        p = re.compile('\+{2,}')
        self.source = p.sub(lambda x: "".join(['x', str(len(x.group())), ';']), self.source)

    '''
    Packs decrements - substracts 4 instead of lowering cell by 1 four times
    '''
    def packDec(self):
        p = re.compile('\-{2,}')
        self.source = p.sub(lambda x: "".join(['_', str(len(x.group())), ';']), self.source)

    '''
    Packs pointer moves
    '''
    def packShift(self):
        p = re.compile('<{2,}')
        self.source = p.sub(lambda x: "".join(['{', str(len(x.group())), ';']), self.source)
        p = re.compile('>{2,}')
        self.source = p.sub(lambda x: "".join(['}', str(len(x.group())), ';']), self.source)

    '''
    Packs conditional set (bool)
    '''
    def packOneIf(self):
        self.source = self.source.replace('[>[-]+<-]', '1S')

    '''
    Packs cell reset - substracting 1 until the cell is 0
    '''
    def packReset(self):
        self.source = self.source.replace('[-]', 'R')

    '''
    Moves values of cell elsewhere
    [>>+<<-] is actually adding current cell value to value of cell 2 shifts right
    '''
    def anyPack(self):
        p = re.compile('\[([R<>+-]{4,})\]')

        found = []
        for match in p.finditer(self.source):
            if (match.group(0) in found):
                # already matched and replaced
                continue
            found.append(match.group(0))
            reset = []
            move = {}
            pos = 0
            for i in match.group(1):
                if '-' == i:
                    if not pos in move:
                        move[pos] = 0
                    move[pos] -= 1
                elif '+' == i:
                    if not pos in move:
                        move[pos] = 0
                    move[pos] += 1
                elif '>' == i:
                    pos += 1
                elif '<' == i:
                    pos -= 1
                else:
                    reset.append(pos)

            if (0 == pos) and (0 in move) and (-1 == move[0]) and (0 not in reset):
                move.pop(0)
                result = 'm'
                for x in reset:
                    result += str(x) + ";"
                result += '0;'
                for (i, x) in move.items():
                    result += str(i) + ';' + str(x) + ';'
                # ukončení
                result += '0;'
                self.source = self.source.replace(match.group(0), result)

    '''
    Manages static data setting (reset and than set data)
    '''
    def staticSet(self):
        self.source = self.source.replace('R', 'RS')
        self.source = self.source.replace(']', ']S')

        # data set after static value
        self.source = self.source.replace('Sx', 's')
        # cleanup
        self.source = self.source.replace('S', '')
        self.source = self.source.replace('Rs', 's')
