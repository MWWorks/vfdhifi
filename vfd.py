import smbus
import time



#split array into chunks
def array_chunk(l, n):
    n = max(1, n)
    return (l[i:i+n] for i in range(0, len(l), n))

def set_bit(v, index, x):
  """Set the index:th bit of v to 1 if x is truthy, else to 0, and return the new value."""
  mask = 1 << index   # Compute mask, an integer with just bit 'index' set.
  v &= ~mask          # Clear the bit indicated by the mask (if x is False)
  if x:
    v |= mask         # If x was True, set the bit indicated by the mask.
  return v            # Return the result, we're done.

def get_bit(x, n):
    # a more bitwise- and performance-friendly version:
    return x & 1 << n != 0

#return the font size byte, so we can pass pixel size
def size_byte(pixels):
    index = [8,16,24,32].index(pixels)
    return 0x30+index

#convert text into byte array
def text_bytes(text):
    if isinstance(text, str): #if we passed text, convert it into byte array
        return list(text.encode())
    else:
        return text #but the option to return just raw byte array

#convert xy into the two bytes needed
#y needs to be multiple of 8
def xy_bytes(x,y):
    address = (x*8)+(y//8)
    h = address//256
    l = address%256
    return l, h

class Vfd:

    def send_command(self, bytes):
#        print(' '.join(format(x, '02x') for x in bytes))
        chunks = array_chunk(bytes, self.maxbytes)
        for chunk in chunks:
            register = chunk.pop(0) ##below command needs to start with one byte
            self.bus.write_i2c_block_data(0x70, register, chunk)

    ##its always on address 70
    def __init__(self, bus = 1, bright = 1, power = 1, maxbytes = 8):
        self.maxbytes = maxbytes
        self.bus = smbus.SMBus(bus)
        self.clear()
        self.set_bright(bright)
        self.set_power(power)

        #regular text placement
#        self.send_command([0x1B,0x4A,0x46,0x31]) #font size
#        self.send_command([0x1B,0x4A,0x57,0x30,0x00,0x00]) #character in top left
#        text = 'hello'
#        bytes = list(text.encode())
#        self.send_command(bytes)



    #pass 0-5
    def set_bright(self, bright):
        self.send_command([0x1B,0x4A,0x44,0x30+bright]) #brightness 30-35, pass

    #pass True or False
    def set_power(self, power):
        self.send_command([0x1B,0x4A,0x42,0x30+int(power)])  #power 30 of 31 on

    def clear(self):
        self.send_command([0x1B,0x4A,0x43,0x44]) #clear display



    #set scroll box - note t and h must be multiples of 8, vfd works in units of 8 for v axis
    def scroll_set_box(self, l, t, w, h, size = 0, line=1):
        bl, bh = xy_bytes(l, t)
        self.send_command([0x1B,0x5D,0x53,bl,bh,w,h//8])
        if size>0:
            self.scroll_set_text(size, line)

    #set size, usually called by the above
    def scroll_set_text(self, size, line = 1):
        self.send_command([0x1B,0x5D,0x42,size_byte(size),line])

    #load text and probably start the scroll
    def scroll_text(self, text, speed = 0, gap = 0, count = 0, start = True, line = 1):
        bytes = text_bytes(text)
        bytes = bytes[:100]
        self.send_command([0x1B,0x5D,0x43,line,len(bytes)])
        self.send_command(bytes)
        if start:
            self.scroll_start(speed, gap, count)

    #load bmp and probably start the scroll
    def scroll_bmp(self, bytes, height, speed = 0, gap = 0, count = 0, start = True, line = 1):

        #dont really understand DM so we will put it into FROM
        lh=len(bytes)//256
        ll=len(bytes)%256
        self.send_command([0x1B,0x6A,0x41,0x31]) #delete
        self.send_command([0x1B,0x6A,0x53,0x31,ll,lh])
        self.send_command(bytes)

        wh=(len(bytes)//(height//8))//256
        wl=(len(bytes)//(height//8))%256
        self.send_command([0x1B,0x5D,0x46,0x31,0,0,height//8,wl,wh])

        if start:
            self.scroll_start(speed, gap, count, True)

    #start it, as above
    def scroll_start(self, speed = 0, gap = 0, count = 0, bmp = False):
        self.send_command([0x1B,0x5D,0x3E,0x30+int(bmp),count,0x30+speed,gap])

    #stop
    def scroll_stop(self):
        self.send_command([0x1B,0x5D,0x3D,0x58])



    def text_write(self, text, l=0, t=0, size=8, clear_line = False):
        bl, bh = xy_bytes(l, t)
        self.send_command([0x1B,0x4A,0x57,0x30,bl,bh]) #set cursor
        self.send_command([0x1B,0x4A,0x46,size_byte(size)]) #set size
        self.send_command(text_bytes(text)) #send text
        if clear_line:
            self.send_command([0x1B,0x5B,0x30,0x4B]) #set size



    def bmp_write(self, l, t, bytes, xdir = True):
        bl, bh = xy_bytes(l, t)
        lh=len(bytes)//256
        ll=len(bytes)%256
        self.send_command([0x1B,0x4A,0x30,bl,bh,0x30+int(xdir),ll,lh])
        self.send_command(bytes)

    def bmp_box_set(self, box, l, t, w, h):
        bl, bh = xy_bytes(l, t)
        self.send_command([0x1B,0x5C,0x42,0x30+box,bl,bh,w,h//8])

    def bmp_box_write(self, box, bytes):
        self.send_command([0x1B,0x5C,0x48,0x30+box])
        lh=len(bytes)//256
        ll=len(bytes)%256
        self.send_command([0x1B,0x5C,0x5D,ll,lh])
        self.send_command(bytes)

    #load from FROM
    def bmp_box_load(self, box, height, sector = 1, start = 0):
        self.send_command([0x1B,0x5C,0x48,0x30+box])
        lh=start//256
        ll=start%256
        self.send_command([0x1B,0x5C,0x46,0x30+sector,ll,lh,height//8])


    #create a font
    def define_font(self, size, glyph, bmp_bytes):

        #bytes we will pass as a friendly-ish array of boolean literals that represents the character, with the no of bits matching the column
        #but it needs transposing into the vertical bytes that the vfd needs
        rows = size
        if(size == 8):
            cols = 6
        elif(glyph<128):
            cols = size/2
        else:
            cols = size

        #this was trial and error rather than actual mathematical logic :|
        bytes = [0x00]*int((rows/8)*cols)
        for row in range(0, rows):
            for col in range(0, cols):
                dest_byte = ((cols-1-col)*(cols//8)) + row//8
                dest_bit = 7-row%8
                bytes[dest_byte] = set_bit(bytes[dest_byte], dest_bit, get_bit(bmp_bytes[row], col))

        if(glyph<128):
            self.send_command([0x1B,0x6A,0x47,size_byte(size),glyph])
        else:
            self.send_command([0x1B,0x6A,0x47,size_byte(size)+3,glyph%256,glyph//256])
        self.send_command(bytes)

