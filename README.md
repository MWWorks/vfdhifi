## VFD hifi

Some misc code sharing from the setup of my VFD-enabled hifi thingy at https://www.mwworks.uk/project/80s-style-hifi-unit-with-vfd-displays

This code is a starting point for anyone wanting to do something similar - it's in no way complete, guaranteed, fit for purpose, etc (and I'm a hack at python).

### vfd.py

This is the driver for the VFD display - it's specifically for a Futaba GP1212A02A. It has various interfaces, but this code is for running it over i2c; you'll need to be able to fashion a cable for it - see https://imgur.com/gallery/7NiOgrQ for some pics. You should also familiarise yourself with the docs for it. Sample usage:

    from vfd import Vfd

    #----------
    #set up vfd
    #----------
    vfd = Vfd()
    vfd.clear()
    vfd.set_power(True)
    vfd.set_bright(3)
    vfd.text_write('Hello world', 0, 0, 8, True)
    
## hifieq.py

This is the service that monitors the equalizers and then renders any changes in the form of adjustments to the alsa equalizer or mbeq plugin - I had better luck with the 10-band equal plugin. You may need a bit of familiarity/homework with ALSA/asound.conf to get this working.

## hifimpd.py

This actually runs the display - polling Mopidy (via MPD) for updates - and handles the button presses. Not it uses two methods for drawing text:

* Native text display of the VFD
* Rendering text into a bitmap and sending that

The latter was to be able to display full unicode characters for eg CJK song and artist names. It uses this library:

https://gist.github.com/dbader/5488053

I tried many fonts but ARIALUNI seems to render best in mono and have the fullest character set.
