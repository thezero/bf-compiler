'''
Created on 4.11.2010

@author: The Zero
'''

import copy
from langtemplate.pyth import Pyth
from langtemplate.php import Php

'''
Generic token
'''
class Token():
    def __init__(self):
        self.staticValue = None
        self.staticPos = None
        self.prev = None
        self.next = None
        self.pos = None

    def link(self, token):
        self.prev = token
        try:
            token.next = self
        except AttributeError:
            pass

    def setpos(self, pos):
        self.pos = pos

    def setStaticValue(self, value):
        self.staticValue = value
        return self

    def setStaticPos(self, pos):
        self.staticPos = pos
        return self

    def process(self, program):
        return (None, None,)

    def write(self, code):
        raise NotImplementedError('Provide custom write() method for ' + self.__class__.__name__)

    def transform(self, program):
        return None

'''
Generic container, contains tokens inside itself
'''
class Container(Token):
    def __init__(self):
        self.firstToken = Dummy()
        self.lastToken = self.firstToken
        self.stable = None
        self.simple = None
        self.changeWithinBoundary = None
        self.changeWithinBoundaryMax = 0
        self.changeWithinBoundaryMin = 0
        self.changeWithinBoundaryOff = 0
        Token.__init__(self)

    def addToken(self, token):
        token.prev = self.lastToken
        self.lastToken.next = token
        self.lastToken = token

    def close(self):
        return self

    def isStable(self):
        if None == self.stable:
            self.stable = True
            self.simple = True
            token = self.firstToken.next
            offset = 0
            while None != token and True == self.stable:
                if isinstance(token, Data) or isinstance(token, ComplexOp) or isinstance(token, In) or isinstance(token, Out):
                    pass
                elif isinstance(token, Loop):
                    self.stable = token.isStable()
                    self.simple = False
                elif isinstance(token, Move):
                    offset += token.offset
                else:
                    self.stable = False
                token = token.next

            if True == self.stable and 0 != offset:
                self.stable = False

            if False == self.stable and True == self.simple:
                self.simple = False

        return self.stable

    def isChangeWithinBoundary(self):
        if None == self.changeWithinBoundary:
            if self.isStable():
                self.changeWithinBoundary = True
                return True

            token = self.firstToken.next
            offset = 0

            minChange = 0
            maxChange = 0

            while None != token and False != self.changeWithinBoundary:
                if isinstance(token, Out) or isinstance(token, SaveTmp):
                    pass
                elif isinstance(token, Data) or isinstance(token, In):
                    minChange = min(minChange, offset)
                    maxChange = max(maxChange, offset)
                elif isinstance(token, Move):
                    offset += token.offset
                elif isinstance(token, ComplexOp):
                    minChange = min(minChange, offset)
                    maxChange = max(maxChange, offset)
                    for i in token.resets:
                        minChange = min(minChange, offset + i)
                        maxChange = max(maxChange, offset + i)
                    for (i, x) in token.moves.items():
                        minChange = min(minChange, offset + i)
                        maxChange = max(maxChange, offset + i)
                        # just do something with it
                        x += 1
                else:
                    self.changeWithinBoundary = False

                token = token.next

            if False != self.changeWithinBoundary:
                self.changeWithinBoundaryMax = maxChange
                self.changeWithinBoundaryMin = minChange
                self.changeWithinBoundaryOff = offset
                if offset == 0 and self.simple:
                    self.changeWithinBoundary = True
                elif offset > 0 and offset > maxChange:
                    self.changeWithinBoundary = True
                elif offset < 0 and offset < minChange:
                    self.changeWithinBoundary = True
                else:
                    self.changeWithinBoundary = False

        return self.changeWithinBoundary

    def preOptimize(self, program):
        pass

    def process(self, program):
        program.localMemory = LocalMemory()
        staticValue = self.staticValue
        staticPos = self.staticPos

        '''
        calculate loop stability
        '''
        self.stable = self.isStable()

        '''
        process children
        '''
        token = self.firstToken.next
        while None != token:
            if False == self.stable and isinstance(token, Loop):
                token.isStable()
                token.stable = False

            token.setStaticValue(staticValue)
            token.setStaticPos(staticPos)

            if program.optimize['Transform']:
                transformed = token.transform(program)
                temp = transformed
                # keep transforming while you can; tuples are not transformed immediately
                while isinstance(temp, Token):
                    temp = transformed.transform(program)
                    if temp:
                        transformed = temp

                if transformed:
                    first = last = transformed
                    if not isinstance(transformed, Token):
                        first, last = transformed

                    if first and last:
                        token.prev.next = first
                        first.prev = token.prev

                        if token.next:
                            token.next.prev = last
                        last.next = token.next
                        token = first
                    else:
                        # either of pair is "None" (return value was (None, None, )) - telling us to skip this token
                        token.prev.next = token.next
                        try:
                            token.next.prev = token.prev
                        except AttributeError:
                            self.parent.lastToken = token.prev
                        token = token.next
                    staticValue = token.staticValue
                    staticPos = token.staticPos
                    continue

            if isinstance(self, Program) and isinstance(token, Loop) and None != staticPos and program.memory.isStaticValue(staticPos) and 0 == program.memory.getValue(staticPos):
                # loops inside program with static value 0
                token.prev.next = token.next
                token.next.prev = token.prev
                token = token.next
                continue

            staticValue, staticPos = token.process(program)
            if None != staticPos:
                program.maxStaticPos = max(program.maxStaticPos, staticPos)
            token = token.next

        self.preOptimize(program)


        '''
        removes dynamic pos data change - multiple moves back and forth after flattening transformed ComplexOps
        needs to be done before unnecessary shift for packing moves
        '''
        if program.optimize['RemoveData']:
            cells = {}
            relativePtr = 0
            token = self.firstToken.next
            while None != token:
                if None != token.staticPos or None != token.staticValue:
                    token = token.next
                    continue

                if isinstance(token, Move):
                    relativePtr += token.offset

                elif isinstance(token, Data):
                    if relativePtr not in cells or cells[relativePtr] == False:
                        cells[relativePtr] = token
                    else:
                        # merge with first token
                        cells[relativePtr].value = cells[relativePtr].mergeValue(token)
                        token.prev.next = token.next
                        if token.next:
                            token.next.prev = token.prev

                else:
                    cells = {}

                token = token.next
                
        '''
        more cleanups of loops
        '''
        if program.optimize['RelativeData']:
            relativeMemory = LocalMemory()
            
            firstToken = self.firstToken
            token = self.firstToken
            offset = 0
            while None != token:
                if None != token.staticPos:
                    token = token.next
                    continue
                    
                if isinstance(token, Data):
                    if None != token.staticValue:
                        if offset in relativeMemory.data and None != relativeMemory.data[offset]:
                            # offset already set, remove
                            oldToken = relativeMemory.data[offset]
                            oldToken.prev.next = oldToken.next
                            oldToken.next.prev = oldToken.prev
                        
                        relativeMemory.setValue(offset, token)
                    else:
                        relativeMemory.setValue(offset, None)
                elif isinstance(token, Move):
                    offset += token.offset
                elif isinstance(token, Out):
                    if None != token.staticValue:
                        # this memory cannot be optimized
                        relativeMemory.setValue(offset, None)
                else:
                    # token not supported, reset processing
                    relativeMemory = LocalMemory()
                    firstToken = token
                token = token.next

        self.optimizeUnnecessaryShift(program)
        self.optimizeDataOutSwitch(program)
        self.optimizeRemoveData(program)   
        self.optimizeDataOutSwitch(program)
        self.optimizeRemoveData(program)
        
        self.reassignStaticValues(program)
        
        self.optimizeUnnecessaryShift(program)
        self.optimizeDataOutSwitch(program)
        self.optimizeRemoveData(program)

        '''
        creates multiout (print()) tokens
        '''
        if program.optimize['MultiOut']:
            token = self.firstToken
            multi = None
            while None != token:
                prev = token.prev

                if prev and token.staticValue and isinstance(token, Out):
                    if None != multi:
                        multi.append(token.staticValue)
                        multi.next = token.next
                        if multi.next:
                            multi.next.prev = multi
                    elif prev.staticValue and isinstance(prev, Out):
                        multi = MultiOut()
                        multi.setStaticPos(prev.staticPos).setStaticValue(prev.staticValue)
                        multi.append(prev.staticValue)
                        multi.append(token.staticValue)

                        prev.prev.next = multi
                        multi.next = token.next
                        multi.prev = prev.prev
                        if multi.next:
                            multi.next.prev = multi
                    else:
                        multi = None
                else:
                    multi = None
                token = token.next
                
        # remove loops immediately following loops. This mostly happens because of file comments.
        token = self.firstToken.next
        while None != token:
            if isinstance(token, Loop) and isinstance(token.next, Loop):
                token.next = token.next.next
                if None != token.next:
                    token.next.prev = token
            else:
                token = token.next

        program.localMemory = LocalMemory()
        return (staticValue, staticPos, )

    def write(self, code):
        token = self.firstToken
        code.template.debugLoop(self)
        while None != token:
            code.template.debugToken(token)
            token.write(code)
            token = token.next

    def removeTokens(self, type, recursive = True):
        token = self.firstToken.next
        while token:
            if isinstance(token, type):
                token.prev.next = token.next
                try:
                    token.next.prev = token.prev
                except AttributeError:
                    self.lastToken = token.prev
            elif recursive and isinstance(token, Container):
                token.removeTokens(type, recursive)
            token = token.next
            
    def optimizeDataOutSwitch(self, program):
        '''
        puts together out tokens and data tokens
        '''
        if program.optimize['DataOutSwitch']:
            removable = lambda x: isinstance(x, (Loop, ComplexOp, ))
            token = self.firstToken.next
            while None != token:
                next = token.next
                prev = token.prev

                if next and next.staticValue and isinstance(next, Out) and None != token.staticValue and isinstance(token, Data):
                    prev.next = next
                    token.next = next.next
                    token.prev = next
                    next.prev = prev
                    next.next = token
                    continue

                elif isinstance(token, Data) and isinstance(next, Data) and token.staticPos == next.staticPos and None != token.staticPos:
                    prev.next = next
                    next.prev = prev
                    if None == token.staticValue:
                        next.value = token.mergeValue(next)

                elif removable(token) and (removable(next) or (isinstance(next, Reset) and 0 == next.value)) and next.staticPos == token.staticPos and None != token.staticPos:
                    token.next = token.next.next
                    if token.next:
                        token.next.prev = token

                token = token.next
                
    def optimizeRemoveData(self, program):
        '''
        removes Data set which is not required
        '''
        if program.optimize['RemoveData']:
            token = self.firstToken.next
            cells = {}
            while None != token:
                if None == token.staticPos or None == token.staticValue:
                    cells = {}
                    # no optimizing after this point is possible
                    token = None
                    continue

                elif isinstance(token, Data):
                    if token.staticPos not in cells or cells[token.staticPos] == False:
                        # currently no set is saved, this is the token that sets real data
                        cells[token.staticPos] = token

                    else:
                        # some token is already saved, it's not necessary
                        removed = cells[token.staticPos]
                        removed.prev.next = removed.next
                        if removed.next:
                            removed.next.prev = removed.prev
                        cells[token.staticPos] = token

                elif isinstance(token, ComplexOp):
                    raise RuntimeError('ComplexOp with static pos and value found and not morphed')

                token = token.next
                
            token = self.firstToken.next
            while None != token:
                if None == token.next or token.staticPos != token.next.staticPos:
                    token = token.next
                    continue
                
                if isinstance(token, Data) and isinstance(token.next, Reset):
                    token.prev.next = token.next
                    token.next.prev = token.prev
                    
                elif isinstance(token, Reset) and isinstance(token.next, Data):
                    token.next.staticValue = token.next.value
                    
                    token.prev.next = token.next
                    token.next.prev = token.prev
                    
                    value = token.next.staticValue
                    subtoken = token.next.next
                    while None != subtoken:
                        if isinstance(subtoken, Out):
                            subtoken.staticValue = value
                            subtoken = subtoken.next
                        elif isinstance(subtoken, Reset):
                            value = 0
                            subtoken = subtoken.next
                        elif isinstance(subtoken, Data):
                            subtoken.staticValue = value + subtoken.value
                            value = subtoken.staticValue
                            subtoken = subtoken.next
                        else:
                            subtoken = None
                
                token = token.next
                
            # remove remaining tokens - only for program, cannot be done in loops
            if isinstance(self, Program):
                for token in cells.values():
                    token.prev.next = token.next
                    if token.next:
                        token.next.prev = token.prev
                     
    def optimizeUnnecessaryShift(self, program):
        '''
        removes all unnecessary moves (at the beginning with static values)
        '''
        if program.optimize['UnnecessaryShift']:
            '''
            all is static - no need to move at all
            '''
            if self.simple:
                token = self.firstToken.next
                allStatic = True
                while token:
                    if (None == token.staticValue) and not (None != token.staticPos and isinstance(token, (Out, Move, Reset, ComplexOp))):
                        allStatic = False
                        break
                    token = token.next

                if allStatic:
                    self.removeTokens(Move)

            '''
            initial moves
            '''
            token = self.firstToken.next
            offset = 0
            firstPos = token.staticPos
            finalPos = token.staticPos
            skipOne = False
            if isinstance(token, Move) and None != token.staticPos:
                offset = -token.offset
                # if there's only one move, we remove it, but have to re-add it
                skipOne = True
            while token and None != token.staticPos and None != token.staticValue and token.next and None != token.next.staticValue:
                if isinstance(token, Move):
                    finalPos = token.staticPos
                    if token != self.firstToken.next:
                        skipOne = False
                    offset += token.offset
                    token.prev.next = token.next
                    if token.next:
                        token.next.prev = token.prev
                    else:
                        self.lastToken = token.prev
                token = token.next

            if token and not token.next and None != token.staticPos and None != token.staticValue and not isinstance(token, Move):
                # we have reached end and last token is also static, so there's no need to write move
                token = None

            if (token and offset) or skipOne:
                if isinstance(token, Move) and None != token.staticPos and token.next:
                    # last token before dynamic token is move, consume it
                    finalPos = token.staticPos
                    offset += token.offset
                    token.prev.next = token.next
                    token.next.prev = token.prev
                    token = token.next

                move = Move(finalPos - firstPos).setStaticPos(finalPos)
                move.processed = True
                # static value doesn't match
                move.setStaticValue(None)

                token.prev.next = move
                move.prev = token.prev
                token.prev = move
                move.next = token

            lastMove = None
            lastStatic = None
            token = self.firstToken.next
            while token and token.next:
                if None != token.staticPos:
                    lastStatic = token
                    token = token.next
                    
                    if isinstance(token, Move):
                        lastMove = token
                    continue

                if isinstance(token, Move) and isinstance(token.next, Move):
                    if token.offset == -token.next.offset:
                        # skip both
                        token.prev.next = token.next.next
                        if token.next.next:
                            token.next.next.prev = token.prev
                        token = token.next.next
                    else:
                        # merge
                        token.offset += token.next.offset
                        if token.next.next:
                            token.next.next.prev = token
                        token.next = token.next.next
                    continue

                token = token.next
                
            if None != lastMove and None != lastStatic and lastMove != lastStatic:
                lastMove.prev.next = lastMove.next
                if lastMove.next:
                    lastMove.next.prev = lastMove.prev
                
                lastMove.prev = lastStatic
                lastMove.next = lastStatic.next
                lastStatic.next = lastMove
                
    def reassignStaticValues(self, program):
        token = self.firstToken.next
        
        staticValue = token.staticValue
        staticPos = token.staticPos
        memory = Memory(program.maxValue)
        while None != token and None != staticValue and None != staticPos:
            if isinstance(token, Reset):
                if None != token.staticPos:
                    memory.setValue(token.staticPos, 0)
                else:
                    memory.setValue(staticPos, 0)
                    token.setStaticPos(staticPos)                
            elif isinstance(token, Data):
                if None != token.staticValue and None != token.staticPos:
                    memory.setValue(token.staticPos, token.staticValue)
                elif None != token.staticValue:
                    # should not happen, better break cycle
                    staticValue = None
                else:
                    memory.alterValue(staticPos, token.value)
                    token.setStaticPos(staticPos)
                    token.setStaticValue(memory.getValue(staticPos))
            elif isinstance(token, Move):
                if None != token.staticPos:
                    staticPos = token.staticPos
                else:
                    staticPos += token.offset
                    processed = token.processed
                    token.processed = False
                    token.setStaticPos(staticPos)
                    token.setStaticValue(memory.getValue(staticPos))
                    token.processed = processed
            elif isinstance(token, Out):
                if None == token.staticValue and None == token.staticPos:
                    token.setStaticPos(staticPos)
                    token.setStaticValue(memory.getValue(staticPos))
                else:
                    staticValue = None
            else:
                staticValue = None
                
            token = token.next
                

'''
Dummy token for loop init
'''
class Dummy(Token):
    def write(self, code):
        pass

    def process(self, program):
        return (self.staticValue, self.staticPos, )

'''
Whole program
'''
class Program(Container):
    '''
    Program is special loop and is pseudo-stable - allows subloops to be stable
    '''
    def isStable(self):
        self.stable = True
        return True

    def preOptimize(self, program):
        if 0 < self.staticPos:
            # manually process move
            token = Move(self.staticPos).setStaticPos(self.staticPos).setStaticValue(0)
            token.processed = True

            next = self.firstToken.next
            token.next = next
            next.prev = token
            token.prev = self.firstToken
            self.firstToken.next = token

    def process(self, code):
        self.setStaticValue(0)
        self.maxValue = code.maxValue
        self.memory = Memory(code.maxValue)
        self.trackMemory = True

        self.optimize = {
            'DataOutSwitch': True,
            'MultiOut': True,
            'UnnecessaryShift': True,
            'RemoveData': True,
            'Transform': True,
            'RelativeData': True,
        }

        code.memory = self.memory

        pos = 0
        # loops in the beginning are useless, probably a comment, remove
        # move breaks staticValue, get rid of it too
        token = self.firstToken.next
        while isinstance(token, Move) or isinstance(token, Loop) or isinstance(token, Reset) or isinstance(token, ComplexOp):
            if isinstance(token, Move):
                pos += token.offset
            self.firstToken.next = token.next
            token = token.next
            token.prev = self.firstToken

        self.staticPos = pos
        self.maxStaticPos = pos

        Container.process(self, self)

        token = self.firstToken.next
        while token and token.next:
            token = token.next
        # unnecessary data operations at the end
        while isinstance(token, Move) or isinstance(token, Data):
            token = token.prev
            if token:
                token.next.prev = None
                token.next = None
            else:
                self.firstToken = None

        return (0, 0, )

    def write(self, code):
        context = code.template.startProgram()
        pos = None
        if 0 < self.maxStaticPos:
            code.template.initMem(self.maxStaticPos + 1)
            # hack, we shouldn't know about code lines
            pos = len(code.currentToken['lines']) - 1
        Container.write(self, code)
        if False == code.features['data'] and None != pos and isinstance(code.template, (Pyth, Php, )):
            code.currentToken['lines'][pos] = None

        code.template.endProgram(context)

'''
Tokens []
'''
class Loop(Container):
    def __init__(self, parent):
        Container.__init__(self)
        self.parent = parent

    def close(self):
        return self.parent

    def transform(self, program):
        if isinstance(self.lastToken, Reset):
            transformed = IfLoop(self.parent)
            transformed.setStaticValue(self.staticValue).setStaticPos(self.staticPos).setpos(self.pos)
            transformed.firstToken = self.firstToken
            transformed.lastToken = self.lastToken
            transformed.stable = True
            transformed.simple = True

            return transformed

        if self.firstToken.next == self.lastToken:
            if isinstance(self.lastToken, Loop):
                return self.lastToken.setStaticValue(self.staticValue).setStaticPos(self.staticPos)
            elif isinstance(self.lastToken, In):
                transformed = IfLoop(self.parent)
                transformed.setStaticValue(self.staticValue).setStaticPos(self.staticPos).setpos(self.pos)
                transformed.firstToken = self.firstToken
                transformed.lastToken = self.lastToken
                transformed.stable = True
                transformed.simple = True

                return transformed
            elif isinstance(self.lastToken, Move):
                if 1 == self.lastToken.offset:
                    transformed = Find()
                    transformed.setStaticValue(self.staticValue).setStaticPos(self.staticPos).setpos(self.pos)
                    return transformed
                elif self.lastToken.offset < 0 and None != self.staticPos and None != self.staticValue and isinstance(self.parent, Program):
                    # this is a microop for pgq.b - it sets a bunch of data and then seeks back
                    offset = self.staticPos
                    while program.memory.isStaticValue(offset) and 0 != program.memory.getValue(offset) and offset >= 0:
                        offset += self.lastToken.offset
                    if offset >= 0:
                        # if offset is negative, there was some error so we don't optimize
                        transformed = Move(offset - self.staticPos)
                        transformed.setStaticValue(0).setStaticPos(offset).setpos(self.pos)
                        transformed.processed = True
                        return transformed

        if self.staticPos and self.staticValue and self.isChangeWithinBoundary():
            okGo = True

            token = self.firstToken.next
            while token:
                if isinstance(token, (In, )):
                    okGo = False
                token = token.next

            if not okGo:
                return None

            chars = []
            pos = self.staticPos
            while program.memory.isStaticValue(pos) and program.memory.getValue(pos):
                token = self.firstToken.next
                while token:
                    if isinstance(token, Move):
                        pos += token.offset
                        program.memory.isStaticValue(pos)
                    elif isinstance(token, Data):
                        program.memory.alterValue(pos, token.value)
                    elif isinstance(token, ComplexOp):
                        val = program.memory.getValue(pos)
                        if val == 0:
                            token = token.next
                            continue
                        for i in token.resets:
                            program.memory.isStaticValue(pos + i)
                            program.memory.setValue(pos + i, 0)
                        for (i, x) in token.moves.items():
                            program.memory.isStaticValue(pos + i)
                            program.memory.alterValue(pos + i, x * val)
                        program.memory.setValue(pos, 0)
                    elif isinstance(token, Out):
                        chars.append(program.memory.getValue(pos))
                    token = token.next

            dump = DumpMemory(program.memory)
            dump.setStaticPos(pos)
            dump.setStaticValue(program.memory.getValue(pos))

            if len(chars):
                dump.setChars(chars)

            return dump

        return None

    def write(self, code):
        code.features['data'] = True
        if None == self.staticPos:
            code.features['ptr'] = True
        loop = {'lines':[], 'loops':{}}
        code.template.callLoop(self.pos)
        code.currentToken['loops'][self.pos] = loop
        code.stack.append(code.currentToken)
        code.currentToken = loop

        context = code.template.startLoop(self.pos, self.staticPos)
        Container.write(self, code)
        code.template.endLoop(context)

        code.currentToken = code.stack.pop()

    def process(self, program):
        program.memory.mode = Memory.reset
        if False == self.isStable():
            self.setStaticPos(None)
        self.setStaticValue(None)

        staticPos = self.staticPos
        Container.process(self, program)
        self.staticPos = staticPos if True == self.stable else None
        return (0, self.staticPos, )

'''
Loop which ends with zero [...0]
'''
class IfLoop(Container):
    def __init__(self, parent):
        Container.__init__(self)
        self.parent = parent

    def close(self):
        return self.parent

    def transform(self, program):
        if None != self.staticPos:
            val = program.memory.getValue(self.staticPos)
            if None == val:
                return None
            elif 0 == val:
                return (None, None, )

            # skip dummy
            return (self.firstToken.next, self.lastToken, )

    def write(self, code):
        code.features['data'] = True
        if None == self.staticPos:
            code.features['ptr'] = True

        self.isStable()
        if self.simple:
            code.template.startInlineIf(self.staticPos)
            Container.write(self, code)
            code.template.endInlineIf(self.staticPos)
        else:
            loop = {'lines':[], 'loops':{}}
            code.template.callIf(self.pos)
            code.currentToken['loops'][self.pos] = loop
            code.stack.append(code.currentToken)
            code.currentToken = loop
            context = code.template.startIf(self.pos, self.staticPos)
            Container.write(self, code)
            code.template.endIf(context)
            code.currentToken = code.stack.pop()

    def process(self, program):
        self.staticValue = None
        Container.process(self, program)
        return (0, self.staticPos, )

'''
Token [>]
'''
class Find(Token):
    def process(self, program):
        Token.process(self, program)
        self.staticValue = 0
        return (0, self.staticPos, )

    def write(self, code):
        code.template.find()

'''
Tokens +- (and x_)
'''
class Data(Token):
    def __init__(self, value = 0):
        self.value = value
        self.processed = False
        Token.__init__(self)

    def process(self, program):
        if program.trackMemory and None != self.staticPos and program.memory.isStaticValue(self.staticPos):
            if not self.processed:
                self.staticValue = program.memory.alterValue(self.staticPos, self.value)
            program.localMemory.setValue(self.staticPos, self.staticValue)
            return (self.staticValue, self.staticPos, )
        elif None != self.staticValue:
            self.staticValue = (self.staticValue + self.value) % program.memory.maxValue
            return (self.staticValue, self.staticPos, )
        return (None, self.staticPos, )

    def write(self, code):
        code.features['data'] = True
        if None != self.staticValue:
            code.template.staticData(self.staticValue, self.staticPos)
            return

        code.template.data(self.value)

    '''
    Merge current value with next data token

    @return: merged value, int or string
    '''
    def mergeValue(self, next):
        tint = isinstance(self.value, int)
        nint = isinstance(next.value, int)
        value = next.value
        if tint and nint:
            value += self.value
        elif not nint:
            if not tint or self.value > 0:
                value = next.value + ' + ' + str(self.value)
            else:
                value = next.value + ' - ' + str(-self.value)
        else:
            if next.value > 0:
                value = self.value + ' + ' + str(next.value)
            else:
                value = self.value + ' - ' + str(-next.value)

        return value

'''
Tokens <> (and {})
'''
class Move(Token):
    def __init__(self, offset):
        self.offset = offset
        self.processed = False
        Token.__init__(self)

    def setStaticPos(self, pos):
        if not self.processed:
            Token.setStaticPos(self, pos)
        return self

    def setStaticValue(self, value):
        if not self.processed:
            Token.setStaticValue(self, value)
        return self

    def process(self, program):
        if not self.processed:
            self.staticPos = None if None == self.staticPos else self.staticPos + self.offset
            staticValue = None
            if None != self.staticPos and program.memory.isStaticValue(self.staticPos):
                staticValue = program.memory.getValue(self.staticPos)
            self.processed = True
            self.staticValue = staticValue
        return (self.staticValue, self.staticPos, )

    def write(self, code):
        if None != self.staticPos:
            code.template.staticMove(self.staticPos)
        else:
            code.template.move(self.offset)

'''
Prepared data shift
'''
class ComplexOp(Token):
    def __init__(self):
        self.resets = []
        self.moves = {}
        self.emptyVals = []
        self.fixedItems = None
        Token.__init__(self)

    def addReset(self, pos):
        self.resets.append(pos)

    def addMove(self, pos, coef):
        self.moves[pos] = coef

    def process(self, program):
        if program.trackMemory and None != self.staticValue and None != self.staticPos:
            for i in self.resets:
                offset = self.staticPos + i
                if offset < 0: offset = 0
                program.memory.setValue(offset, 0)
                program.localMemory.setValue(offset, 0)

            self.fixedItems = {}
            for (i,x) in self.moves.items():
                offset = self.staticPos + i
                if offset < 0: offset = 0
                if program.memory.isStaticValue(offset):
                    self.fixedItems[i] = program.memory.alterValue(offset, self.staticValue * x)
                    program.maxStaticPos = max(program.maxStaticPos, offset)
                else:
                    self.fixedItems = None
                    self.staticValue = None
                    for (i,x) in self.moves.items():
                        offset = self.staticPos + i
                        if offset < 0: offset = 0
                        program.memory.setValue(offset, None)
                        program.localMemory.setValue(offset, None)
                    break

            if self.fixedItems and self.prev:
                # if we have prev, we can morph to data tokens
                token = Reset().setStaticPos(self.staticPos)
                token.process(program)
                firstToken = token

                for i in self.resets:
                    reset = Reset().setStaticPos(self.staticPos).setStaticValue(0)
                    reset.process(program)
                    reset.link(token)
                    token = reset

                for (i, x) in self.fixedItems.items():
                    offset = self.staticPos + i
                    if offset < 0: offset = 0
                    reset = Data().setStaticPos(offset).setStaticValue(x)
                    reset.link(token)
                    token = reset

                firstToken.prev = self.prev
                firstToken.prev.next = firstToken
                token.next = self.next
                if token.next:
                    token.next.prev = token

            program.memory.setValue(self.staticPos, 0)
            program.localMemory.setValue(self.staticPos, 0)

        elif program.trackMemory and None != self.staticPos:
            for i in self.resets:
                offset = self.staticPos + i
                if offset < 0: offset = 0
                program.memory.setValue(offset, 0)
                program.localMemory.setValue(offset, 0)
                program.maxStaticPos = max(program.maxStaticPos, offset)

            for (i,x) in self.moves.items():
                offset = self.staticPos + i
                if offset < 0: offset = 0
                if 0 == program.localMemory.getValue(offset):
                    self.emptyVals.append(offset)
                program.memory.setValue(offset, None)
                program.localMemory.setValue(offset, None)
                program.maxStaticPos = max(program.maxStaticPos, offset)

            program.memory.setValue(self.staticPos, 0)
            program.localMemory.setValue(self.staticPos, 0)

        return (0, self.staticPos, )

    def transform(self, program):
        guessData = isinstance(self.prev, Data) and None == self.prev.staticPos and None == self.prev.staticValue and not len(self.resets)
        if None == self.staticValue and None == self.staticPos and (isinstance(self.prev, Dummy) or guessData):
            # a) first if in loop, can make use of shift opt
            # b) after data change, most likely to set some var (otherwise add zero, some dead code, no problem)

            change = 0
            if isinstance(self.prev, Data):
                # consume prev dynamic data because we reset this cell anyway
                change = self.prev.value
                self.prev.prev.next = self
                self.prev = self.prev.prev

            firstToken = SaveTmp(change)
            firstToken.setStaticPos(self.staticPos)
            next = Reset().setStaticPos(self.staticPos)
            next.link(firstToken)
            current = next

            offset = 0
            for i in self.resets:
                if None == self.staticPos:
                    offset = i - offset
                    next = Move(offset)
                    next.link(current)
                    current = next

                    reset = Reset()
                    reset.link(current)
                    current = reset

                    offset = i
                else:
                    reset = Reset()
                    reset.setStaticPos(self.staticPos + i)
                    reset.link(current)
                    current = reset

            for (i, x) in self.moves.items():
                num = 'tmp'
                if -1 == x:
                    num = '-tmp'
                elif 1 != x:
                    num += ' * ' + str(x)

                if None == self.staticPos:
                    offset = i - offset
                    next = Move(offset)
                    next.link(current)
                    current = next

                    next = Data(num)
                    next.link(current)
                    current = next

                    offset = i
                else:
                    raise NotImplementedError()

            next = Move(-offset)
            next.link(current)
            current = next

            return (firstToken, current, )
        elif None == self.staticPos and None != self.staticValue:
            if 0 == self.staticValue:
                return None
            
            first = None
            token = None
            
            offset = 0
            for i in self.resets:
                offset = i - offset
                move = Move(offset)
                reset = Reset()
                
                if None == first:
                    first = move
                    
                if None != token:
                    token.next = move
                move.next = reset
                move.prev = token
                reset.prev = move
                token = reset
                offset = i
                
            for (i, x) in self.moves.items():
                offset = i - offset
                move = Move(offset)
                data = Data(self.staticValue * x)
                
                if None == first:
                    first = move
                    
                if None != token:
                    token.next = move   
                move.next = data
                move.prev = token
                data.prev = move
                token = data
                offset = i

            offset = -offset
            if offset:
                move = Move(offset)
                
                if None == first:
                    first = move
                if None != token:
                    token.next = move
                move.prev = token
                token = move
                
            reset = Reset()
            if None == first:
                first = reset
            if None != token:
                token.next = reset
            reset.prev = token
            token = reset
            
            return (first, token, )

    def write(self, code):
        isFirst = isinstance(self.prev, Dummy)
        if None == self.staticValue:
            if None == self.staticPos:
                code.features['move'] = True
                code.features['data'] = True
                code.features['dataop'] = True
                code.features['ptr'] = True

            context = None
            if not isFirst:
                context = code.template.startInlineIf(self.staticPos)
            code.template.tmp(0, self.staticPos)
            Reset().setStaticPos(self.staticPos).write(code)

            offset = self.writeResets(code)

            for (i, x) in self.moves.items():
                if None == self.staticPos:
                    offset = i - offset
                    code.template.move(offset)
                    code.template.tmpData(x)
                    offset = i
                else:
                    pos = self.staticPos + i
                    if pos in self.emptyVals:
                        x = None
                    code.template.tmpData(x, pos)

            offset = -offset
            if offset:
                code.template.move(offset)
            if not isFirst:
                code.template.endInlineIf(context)

        elif 0 == self.staticValue:
            pass

        else:
            code.features['move'] = True
            code.features['data'] = True
            code.features['dataop'] = True
            code.features['ptr'] = True
            offset = self.writeResets(code)

            for (i, x) in self.moves.items():
                offset = i - offset
                code.template.move(offset)
                code.template.data(self.staticValue * x)
                offset = i

            offset = -offset
            if offset:
                code.template.move(offset)
            Reset().setStaticPos(self.staticPos).write(code)

    '''
    Writes cell resets to code, returns offset against start position
    '''
    def writeResets(self, code):
        offset = 0
        for i in self.resets:
            if None == self.staticPos:
                offset = i - offset
                code.template.move(offset)
                Reset().write(code)
                offset = i
            else:
                Reset().setStaticPos(self.staticPos + i).write(code)
        return offset

'''
Helper token for ComplexOp
'''
class SaveTmp(Token):
    def __init__(self, change = 0):
        self.change = change
        Token.__init__(self)

    def write(self, code):
        code.template.tmp(self.change, self.staticPos)

'''
Token ,
'''
class In(Token):
    def process(self, program):
        self.setStaticValue(None)
        if None != self.staticPos:
            program.memory.setValue(self.staticPos, None)
            program.localMemory.setValue(self.staticPos, None)
        return (None, self.staticPos)

    def write(self, code):
        code.template.cin()

'''
Token .
'''
class Out(Token):
    def __init__(self, offset = 0):
        self.offset = offset
        Token.__init__(self)

    def process(self, program):
        if program.trackMemory and None != self.staticPos and program.memory.isStaticValue(self.staticPos):
            self.staticValue = program.memory.getValue(self.staticPos)

        return (self.staticValue, self.staticPos, )

    def write(self, code):
        if None != self.staticValue:
            code.template.out(self.staticValue % code.maxValue)
        else:
            code.template.out(None, self.staticPos)

'''
More . tokens after each other
'''
class MultiOut(Token):
    def __init__(self):
        self.chars = []
        Token.__init__(self)

    def process(self, program):
        return (self.staticValue, self.staticPos, )

    def append(self, char):
        if len(self.chars) and ((10 == char and 13 == self.chars[-1]) or (13 == char and 10 == self.chars[-1])):
            return
        self.chars.append(char)

    def write(self, code):
        code.template.multiOut(self.chars)

'''
Token 0
'''
class Reset(Data):
    def __init__(self, value = 0):
        Data.__init__(self, 0)

    def process(self, program):
        self.staticValue = self.value
        if program.trackMemory and None != self.staticPos:
            program.memory.setValue(self.staticPos, self.value)
            program.localMemory.setValue(self.staticPos, self.value)
        return (self.value, self.staticPos, )

    def write(self, code):
        self.staticValue = 0
        Data.write(self, code)

class DumpMemory(Token):
    def __init__(self, memory):
        self.memory = copy.deepcopy(memory)
        self.chars = None
        Token.__init__(self)

    def setChars(self, chars):
        self.chars = MultiOut()
        for i in chars:
            self.chars.append(i)

    def transform(self, program):
        firstToken = Dummy()
        lastToken = firstToken

        pos = self.staticPos
        for (i, x) in self.memory.data.items():
            token = Move(i - pos)
            pos = i
            token.setStaticPos(pos)
            token.setStaticValue(self.memory.data[pos])
            token.processed = True

            token.link(lastToken)
            lastToken = token

            token = Data(x)
            token.setStaticPos(i)
            token.setStaticValue(x)
            token.processed = True

            token.link(lastToken)
            lastToken = token

        token = Move(self.staticPos - pos)
        token.setStaticPos(self.staticPos)
        token.setStaticValue(self.memory.data[self.staticPos])
        token.processed = True

        token.link(lastToken)
        lastToken = token

        if self.chars:
            self.chars.setStaticPos(token.staticPos)
            self.chars.setStaticValue(token.staticValue)
            self.chars.link(lastToken)
            lastToken = self.chars

        program.maxStaticPos = max(program.maxStaticPos, max(self.memory.data.keys()))

        return (firstToken.next, lastToken, )

    def process(self, memory):
        raise RuntimeError('Cannot process temp token DumpMemory')

class Memory():
    fill = 1
    reset = 2

    def __init__(self, maxValue):
        self.data = {}
        self.maxValue = maxValue
        self.mode = self.fill

    def isStaticValue(self, ptr):
        if self.mode == self.reset:
            return False
        if ptr not in self.data:
            self.data[ptr] = 0
        return None != self.data[ptr]

    def alterValue(self, ptr, value):
        if self.mode == self.reset:
            self.data[ptr] = None
        else:
            self.data[ptr] = (self.data[ptr] + value) % self.maxValue
        return self.data[ptr]

    def setValue(self, ptr, value):
        self.data[ptr] = value if self.mode == self.fill else None

    def getValue(self, ptr):
        if self.mode == self.reset:
            return None
        return self.data[ptr]

class LocalMemory():
    def __init__(self):
        self.data = {}

    def setValue(self, ptr, value):
        self.data[ptr] = value

    def getValue(self, ptr):
        if ptr not in self.data:
            return None
        return self.data[ptr]
