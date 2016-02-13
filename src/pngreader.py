'''
Created on 25.1.2010

@author: The Zero
'''
from struct import unpack
from copy import copy
from zlib import decompress

'''
Reads PNG image and creates data structure with information about it
'''
class Png():
    '''
    Constructor

    @param file: image filename
    '''
    def __init__(self, file):
        self.src = open(file, mode='rb')
        self.png = {'prolog': None, 'hdr': None, 'chunks': b'', 'data': [], 'image': []}

    '''
    Reads image
    '''
    def read(self):
        self.png['prolog'] = unpack('8B', self.src.read(8))
        if ((0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, ) != self.png['prolog']):
            # not a PNG or corrupt header
            raise RuntimeError('File is not PNG')

        hdrLen, chType = self.getChunkInfo()
        # first chunk must by 13-char IHDR
        if ((0x49, 0x48, 0x44, 0x52,) != chType):
            raise RuntimeError('IHDR expected')
        if (13 != hdrLen):
            raise RuntimeError('Unknown header')

        # reads IHDR info
        hdr = unpack('>2L5B', self.src.read(13))
        # crc
        unpack('>L', self.src.read(4))
        self.png['hdr'] = {
            'width': hdr[0],
            'height': hdr[1],
            'bpp': hdr[2],
            'ctype': hdr[3],
            'cmethod': hdr[4],
            'filter': hdr[5],
            'interlace': hdr[6]
        }
        self.createChunks()
        self.createData()
        self.createImage()

        self.src.close()

    '''
    Reads basic image chunk info

    @return: tuple (header length, chunk type, )
    '''
    def getChunkInfo(self):
        hdrLen, = unpack('>L', self.src.read(4))
        chType = unpack('4B', self.src.read(4))

        return (hdrLen, chType, )

    '''
    Reads all chunks
    '''
    def createChunks(self):
        while True:
            hdrLen, chType = self.getChunkInfo()
            if ((73, 69, 78, 68,) == chType):
                # IEND
                return
            if ((73, 68, 65, 84,) == chType):
                # IDAT
                self.png['chunks'] = self.png['chunks'] + self.getChunkData(hdrLen)

    '''
    Returns raw data from chunk. Doesn't check CRC

    @param len: chunk length
    @return: chunk data
    '''
    def getChunkData(self, len):
        encoded = self.src.read(len)
        # crc
        unpack('>L', self.src.read(4))
        return encoded

    '''
    Creates real data from chunks
    '''
    def createData(self):
        decoded = decompress(self.png['chunks'])
        for i in range(0, self.png['hdr']['height']):
            start = i * (self.png['hdr']['width'] * 3 + 1)
            data = [int(decoded[start])]
            for j in range(0, self.png['hdr']['width']):
                jStart = start + j*3 + 1
                data.append(unpack('>3B', decoded[jStart:(jStart+3)]))
            self.png['data'].append(data)
        self.png['chunks'] = None

    '''
    Creates image data from uncompressed data
    Reads line by line and applies filter functions to each
    '''
    def createImage(self):
        for line in self.png['data']:
            filter = line[0]
            self.png['image'].append(self.filter(line[1:], filter))
        self.png['data'] = None

    '''
    Creates image data from data line

    @param line: list of data numbers
    @param filter: filter id
    @return: list of image data
    '''
    def filter(self, line, filter):
        data = []
        if (0 == filter):
            return line
        elif (1 == filter):
            prev = (0, 0, 0,)
            for i in line:
                prev = self.add(i, prev)
                data.append(prev)
        elif (2 == filter):
            prev = self.prevLine()
            for (i, x) in enumerate(line):
                data.append(self.add(x, prev[i]))
        elif (3 == filter):
            prevPix = (0, 0, 0, )
            prevLine = self.prevLine()
            for (i, x) in enumerate(line):
                prevPix = self.add(x, map(lambda x: x //2, self.add(prevPix, prevLine[i], limit = False)) )
                data.append(prevPix)
        elif (4 == filter):
            prevPix = (0, 0, 0, )
            prevLine = copy(self.prevLine())
            prevLine.insert(0, prevPix)
            for (i, x) in enumerate(line):
                paeth = (
                           self.paeth(prevPix[0], prevLine[i+1][0], prevLine[i][0]),
                           self.paeth(prevPix[1], prevLine[i+1][1], prevLine[i][1]),
                           self.paeth(prevPix[2], prevLine[i+1][2], prevLine[i][2])
                        )
                prevPix = self.add(x, paeth)
                data.append(prevPix)
        return data

    '''
    Addition method with controlled overflow

    @param a: tuple of image data from cell A
    @param b: tuple of image data from cell B
    @param limit: use 256 color limit, default true
    '''
    def add(self, a, b, limit = True):
        if True == limit:
            return ((a[0]+b[0]) % 256, (a[1]+b[1]) % 256, (a[2]+b[2]) % 256,)
        else:
            return (a[0]+b[0], a[1]+b[1], a[2]+b[2],)

    '''
    Returns previously processed line

    @return: previously processed line or line with (0,0,0,) pixels if no line has been processed
    '''
    def prevLine(self):
            if (0 < len(self.png['image'])):
                return self.png['image'][-1]
            else:
                return (0, 0, 0,) * self.png['hdr']['width']

    '''
    Paeth predictor function for #4 filter

    @param a: tuple of image data from cell A
    @param b: tuple of image data from cell B
    @param c: tuple of image data from cell C
    @return: predicted tuple of image data
    '''
    def paeth(self, a, b, c):
        p = a + b - c
        pa = abs(p - a)
        pb = abs(p - b)
        pc = abs(p - c)
        if pa <= pb and pa <= pc:
            return a
        elif pb <= pc:
            return b
        else:
            return c

# debug mode
if __name__ == '__main__':
    png = Png('hellobl.png')
    png.read()
