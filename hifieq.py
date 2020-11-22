import sys
import time
import signal
import RPi.GPIO as GPIO
import spidev
import alsaaudio



#--------------------
#drive led transistor
#--------------------
#later move this to mpd to i can sleep the leds with the vfd
GPIO.setmode(GPIO.BCM)
GPIO.setup(18,GPIO.OUT)
pwm = GPIO.PWM(18, 200)
pwm.start(10)



#---------
#spi setup
#---------
#create 2 spi objects for each channel, setting the speed is important, after opening
spi = [spidev.SpiDev(), spidev.SpiDev()]
spi[0].open(0, 0)
spi[0].max_speed_hz=500000
spi[1].open(0, 1)
spi[1].max_speed_hz=500000



#----------------
#handle control c
#----------------
def signal_handler(sig, frame):
    pwm.stop()
    GPIO.output(18,GPIO.LOW)
    spi[0].close()
    spi[1].close()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)



#-------------------------
#set up vars for main loop
#-------------------------
equal_type = 'equal' #we have alsamixer and mbeq - defined in asound.conf
values = [0]*10
last_values = [0]*10
eqcontrols = alsaaudio.mixers(-1, equal_type)



#---------
#main loop
#---------
while True:

    #read adc values - i did not come up with the maths!
    #but return as a percentage, we can put this straight into alsaequal
    for device in [0, 1]:
        for index, channel in enumerate([1,0,4,2,3]):
            adc = spi[device].xfer2([1,(8+channel)<<4,0])
            data = ((adc[1]&3) << 8) + adc[2]
            vindex = (device*5)+index
            values[vindex]=data

            if equal_type == 'equal':
                #effective range of alsa eq seems to be 40-90, so lets scale it to that
                values[vindex]=round(data/1024*50)+30
            else:
                #mbeq seems better but still stick to 90 max, but set 60 as centre
                centre = 490
                if(data<centre):
                    values[vindex]=round(data/centre*60)
                else:
                    values[vindex]=round((data-centre)/(1024-centre)*30)+60


    #we allow 1% difference without bothering to update
    update_count = 0
    for index, value in enumerate(values):
        if abs(value-last_values[index])>2:
            update_count = update_count+1;

    #there is some noise in the circuit somehow, making all the values waver
    #so we'll only update if only one slider has changed - a chance in more is probably noise
    if update_count:
        print(values)
        if equal_type == 'equal':
            #alsaequ is straight map
            mixervals = values
        else:
            #mbeq needs interpolating - loop is fiddly, fuck it
            mixervals = [
                values[0], (values[0]+values[1])//2, values[1],
                values[2], (values[2]+values[3])//2, values[3],
                values[4], (values[4]+values[5])//2, values[5],
                values[6], (values[6]+values[7])//2, values[7],
                values[8], (values[8]+values[9])//2, values[9],
            ]

        for index, eqcontrol in enumerate(eqcontrols):
            mixer = alsaaudio.Mixer(eqcontrol, 0, -1, equal_type)
            mixer.setvolume(mixervals[index])

    #important to copy this - just assigning was a gotcha, it does so by reference
    last_values = values.copy()



    time.sleep(0.1) 
