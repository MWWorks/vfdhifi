# i2ctest.py
# A brief demonstration of the Raspberry Pi I2C interface, using the Sparkfun
# Pi Wedge breakout board and a SparkFun MCP4725 breakout board:
# https://www.sparkfun.com/products/8736

import sys
import time
import signal
import ftfont
from mpd import MPDClient
from vfd import Vfd
from gpiozero import Button




#----------
#set up vfd
#----------
vfd = Vfd()
vfd.clear()
vfd.set_power(True)
vfd.set_bright(3)



#----------
#set up mpd
#----------
client = MPDClient()               # create client object
client.connect("localhost", 6600)  # connect to localhost:6600
client.consume(0)



#----------------
#handle control c
#----------------
def signal_handler(sig, frame):
    print('Power off VFD')
    vfd.set_power(False)
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)



#--------------
#set up buttons
#--------------

#define buttons, each one gets a pin and a current type - maybe they will get context sensitive
buttons = [
    {'type': '', 'state': 0, 'pin': 17, 'x': 14},
    {'type': '', 'state': 0, 'pin': 27, 'x': 42},
    {'type': '', 'state': 0, 'pin': 22, 'x': 70},
    {'type': '', 'state': 0, 'pin': 23, 'x': 187},
    {'type': '', 'state': 0, 'pin': 24, 'x': 215},
    {'type': '', 'state': 0, 'pin': 25, 'x': 243},
]

#load button definitions from file - it has binary bitmaps so keep it separate
from button_types import button_types

#set a button to a specific type (action)
def setButton(bpos, btype, label = ''):
    buttons[bpos]['type'] = btype

    #write an image if we passed one for the type
    if len(button_types[btype]['bitmap'])>0:
        x = buttons[bpos]['x']-8
        glyph = button_types[btype]['glyph']
        vfd.text_write([glyph//256,glyph%256], x, 48, 16)
    #otherwise use the button labep
    else:
        if label == '':
            label = button_types[btype]['label']
        x = buttons[bpos]['x']
        x = x-((len(label)*6)//2)
        vfd.text_write(label, x, 56, 8)

#actually perform a button action, here we need to case out all the button types
def doButton(zbutton):

    #we get passed the button object, so find out where it is in our button array
    global buttons
    for i, button in enumerate(buttons):
        if button['pin'] == zbutton.pin.number:
            bpos = i

    mpd_status = client.status()
    vol = 0 if 'volume' not in mpd_status else int(mpd_status['volume'])
    btype = buttons[bpos]['type']

    if btype == 'next':
        client.next()

    elif btype == 'prev':
        client.previous()

    elif (btype == 'toggle' and mpd_status['state'] == 'play') or btype == 'pause':
        client.pause(1)
        setButton(bpos, 'play')

    elif (btype == 'toggle' and mpd_status['state'] != 'play') or btype == 'play':
        client.pause(0)
        setButton(bpos, 'pause')

    elif btype == 'rnd':
        client.random(1)
        setButton(bpos, 'seq')

    elif btype == 'seq':
        client.random(0)
        setButton(bpos, 'rnd')

    elif btype == 'vup' and vol < 100:
        client.setvol(vol+3)
        drawVol()

    elif btype == 'vdn' and vol > 0:
        client.setvol(vol-3)
        drawVol()

#start glyph is arbitrary - just somewhere in the table that we are not using
glyph = 0x8260
for button_type in button_types:
    if(len(button_types[button_type]['bitmap'])>0):
        button_types[button_type]['glyph'] = glyph
        vfd.define_font(16, glyph, button_types[button_type]['bitmap']) #vfd handles transposing of the bitmap
        glyph = glyph +1

#create the button objects
for button in buttons:
    if button['pin']>0:
        button['zbutton'] = Button(button['pin'])
        button['zbutton'].when_pressed = doButton

#and finally create the initial map of buttons to positions
setButton(0, 'prev')
setButton(1, 'pause')
setButton(2, 'next')
setButton(3, 'vdn')
setButton(4, 'vup')
setButton(5, 'rnd')



#-------------------------
#get what we need from mpd
#-------------------------
def getMpdStatus():

    status_artist = ''
    status_track = ''
    status_player = ''
    status_time = ''
    status_pos = ''

    mpdstatus = client.status()
    if 'songid' in mpdstatus:
        if(int(mpdstatus['songid'])>0):

            mpdsong = client.playlistid(mpdstatus['songid'])
            mpdsong = mpdsong[0]
            mpdsong = client.currentsong()

            if 'name' in mpdsong:
                status_artist = mpdsong['name'] #mpd returns radio station in name field
            elif 'albumartist' in mpdsong:
                status_artist = mpdsong['albumartist'] #prefer album artist here
            elif 'artist' in mpdsong:
                status_artist = mpdsong['artist'] #otherwise track artist
            else:
                status_artist = ''

            if 'album' in mpdsong:
                status_artist = status_artist + ' | ' + mpdsong['album']

            if 'title' in mpdsong:
                status_track = mpdsong['title']

            #if album and track artist are different, we used album artist above
            if ('albumartist' in mpdsong) & ('artist' in mpdsong):
                if mpdsong['albumartist']!=mpdsong['artist']:
                    status_track = status_track + ' ('+mpdsong['artist']+')' #so append track artist to the track title

            status_pos = str(int(mpdstatus['song'])+1)+'/'+mpdstatus['playlistlength']

            if 'time' in mpdstatus:
                mpdstatus['time'] = int(round(float(mpdstatus['time'].replace(':', '.'))))
                if mpdstatus['time']>3600:
                    status_time = time.strftime('%H:%M:%S', time.gmtime(mpdstatus['time']))
                else:
                    status_time = time.strftime('%-M:%S', time.gmtime(mpdstatus['time']))
                if 'time' in mpdsong and int(mpdsong['time'])>0:
                    mpdsong['time'] = int(round(float(mpdsong['time'].replace(':', '.'))))
                    if mpdsong['time']>3600:
                        status_time = status_time+'/'+time.strftime('%H:%M:%S', time.gmtime(mpdsong['time']))
                    else:
                        status_time = status_time+'/'+time.strftime('%-M:%S', time.gmtime(mpdsong['time']))

    return {'artist': status_artist, 'track': status_track, 'time': status_time, 'pos': status_pos, 'volume':  mpdstatus['volume'], 'status': mpdstatus}


#-----------
#draw volume
#-----------

#this is out of the main loop so i can draw it immediately afte a button press, instead of waiting for the next second in the loop
def drawVol():
    mpd_status = client.status()
    volpix = int(int(mpd_status['volume'])/2) #we are using 50 pixels for the bar
    bytes = [
       0b00011100,
       0b00011100,
       0b00111110,
       0b01111111,
       0b00000000,
       0b00001000,
       0b00100010,
       0b00011100,
       0b00000000,
       0b00000000,
    ]
    bytes = bytes + [0b01111111]
    bytes = bytes + [0b01111111]*volpix
    bytes = bytes + [0b01000001]*(50-volpix)
    bytes = bytes + [0b01111111]
    x = 92
    y = 0
    vfd.bmp_write(x, y, bytes)
    vfd.text_write(mpd_status['volume'].ljust(3), x+len(bytes)+1, y, 8)


#-----------------------
#now start the main loop
#-----------------------

bmp_mode = True
start_time=time.time()
last_mpd_lines = {'artist': '', 'track': '', 'time': '', 'pos': '', 'status': '', 'volume': ''}
#define status lines for artist and track
lines = [
    {'y': 40, 'action': '', 'status': '', 'bitmap': '', 'max_chars': 42, 'vfd_size': 8,  'key': 'artist' },
    {'y': 16, 'action': '', 'status': '', 'bitmap': '', 'max_chars': 32, 'vfd_size': 16, 'key': 'track'},
]

if bmp_mode:
    #we will fake 2 16px lines by padding out the smaller one
    lines[0]['y'] = 32
    lines[0]['font'] = ftfont.Font('font/ARIALUNI.TTF', 11) #9 seems to get 10
    lines[1]['font'] = ftfont.Font('font/ARIALUNI.TTF', 14) #actually targeting 16px, but with this combination, accents nudge it to 16


#main loop here repeats quickly, but updates mpd only every second
while True:

    #get the current mpd status
    mpd_lines = getMpdStatus()
    mpd_status = mpd_lines['status']

    #now check if any buttons need updating based on the status
    for i, button in enumerate(buttons):
        if button['type'] == 'play' and  mpd_status['state'] == 'play':
            setButton(i, 'pause')
        elif button['type'] == 'pause' and  mpd_status['state'] != 'play':
            setButton(i, 'play')
        elif button['type'] == 'rnd' and  mpd_status['random'] == '1':
            setButton(i, 'seq')
        elif button['type'] == 'seq' and  mpd_status['random'] == '0':
            setButton(i, 'rnd')


    #update the time and position
    vfd.text_write(mpd_lines['pos'].ljust(15), 0, 0, 8, True)
    vfd.text_write(mpd_lines['time'].rjust(14), 256-(6*14), 0, 8, True)

    #song/artist update
    #------------------
    #herein follows some overly complex logic to decide what to do or change
    #the vfd can only do one scroll, so we scroll artist or song as required, with preference for song
    #each time any scroll text is stopped, we have to stop the scroll first
    #so we monitor the status of each line as to what its currently doing


    for index, line in enumerate(lines):
        line['action'] = ''
        line['value'] = mpd_lines[line['key']]
        line['last_value'] = last_mpd_lines[line['key']]
        if line['value'] and line['value']!=line['last_value']:

            if bmp_mode:
                line['bitmap'] = line['font'].render_text(line['value'])
                line['action'] = 'scr' if line['bitmap'].width>256 else 'txt'

                                #for artist line, this is smaller, but padding it out here to  make it also a 16px line_action
                #since we are hardcoding some of the 16-height-ness to this
                if index == 0:
                    pad = (16-(line['bitmap'].height))//2
                    line['bitmap'].height = line['bitmap'].height+pad;
                    line['bitmap'].pixels = bytearray(line['bitmap'].width * pad) + line['bitmap'].pixels

                #and pad both lines to the correct height - the bitmap is truncated if eg there are no descenders

                line['bitmap'].pixels = line['bitmap'].pixels + bytearray(line['bitmap'].width * (16-line['bitmap'].height))
                line['bitmap'].height = 16;

                #now transpose the bitmap into a byte array suitable for the vfd
                #ideally vfd would do this but this bytearray is already a bit janky for the purpose, id have to convert it here anyway
                line['bytes'] = [0x00]*(line['bitmap'].width*2)
                for row in range(0, line['bitmap'].height):
                    for col in range(0, line['bitmap'].width):
                        source_byte = (row*line['bitmap'].width) + col
                        if line['bitmap'].pixels[source_byte]>0:
                            dest_byte = col*2 + (1 if row > 7 else 0)
#                            dest_byte = col+(row//8*line['bitmap'].width)
                            dest_bit = 7-(row%8)
                            line['bytes'][dest_byte] = line['bytes'][dest_byte] | (1<<dest_bit)

            else:
                line['action'] = 'scr' if len(line['value'])>line['max_chars'] else 'txt'


    #if track is text and artist is long, and not scrolling, scroll it
    if len(lines[0]['value'])>lines[0]['max_chars'] and lines[0]['status'] == 'txt' and lines[1]['action'] == 'txt':
        lines[0]['action'] = 'scr'

    #if we are scrolling title, switch artist to text if it's scrolling or set to scroll
    if (lines[1]['action'] == 'scr' and (lines[0]['action'] == 'scr' or lines[0]['status'] == 'scr')):
        lines[0]['action'] = 'txt'

    #likewise if song is currently scrolling, and we are set to scroll artist, dont
    if (lines[0]['action'] == 'scr' and (lines[1]['action'] == '' and lines[1]['status'] == 'scr')):
        lines[0]['action'] = 'txt'

    #stop the scroll if any change in scroll operation required
    if ( (lines[0]['status'] == 'scr' and (lines[0]['action'] or lines[1]['action'] == 'scr'))
         or
         (lines[1]['status'] == 'scr' and (lines[1]['action'] or lines[0]['action'] == 'scr'))
       ):
        vfd.scroll_stop()

    #now actually make changes required
    for index, line in enumerate(lines):

        #remember current status
        if line['action']:
            line['status'] = line['action']

        if line['action'] == 'txt':
            if bmp_mode:
                line['bytes'] = line['bytes'][0:511] #truncate it
                line['bytes'] = line['bytes']+([0x00]*(512-len(line['bytes']))) #pad it to fill screen
                vfd.bmp_box_set(index+1, 0, line['y'], 0, 16)
                vfd.bmp_box_write(index+1, line['bytes'])
            else:
                vfd.text_write(line['value'].ljust(line['max_chars']), 0, line['y'], line['vfd_size'], True)

        elif line['action'] == 'scr':
            if bmp_mode:
                vfd.scroll_set_box(0,line['y'],256,16)
                vfd.scroll_bmp(line['bytes'], 16, speed = 0, gap = 64)
            else:
                vfd.scroll_set_box(0,line['y'],256,line['vfd_size'],line['vfd_size'])
                vfd.scroll_text(line['value'], speed = 0, gap = 64)

    #check for volume change and redraw it if required
    if mpd_lines['volume'] != last_mpd_lines['volume']:
        drawVol()

    #finally, rember the status so we can check next time if it changes; and sleep until the next full second
    last_mpd_lines = mpd_lines
    now_time = time.time()
    time.sleep(1.0 - ((now_time-start_time) - int(now_time-start_time)) )



