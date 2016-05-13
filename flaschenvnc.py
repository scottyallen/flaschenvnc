#!/usr/bin/env python
"""
VNC to Flaschen-Taschen bridge.

Usage:
  python flaschenvnc.py -h 127.0.0.1 -p 'password'

Based on code by Chris Liechti: http://homepage.hispeed.ch/py430/python/

MIT License
"""

SHOW_FRAMERATE_EVERY = 1

import flaschen

#twisted modules
from twisted.python import usage, log
from twisted.internet import reactor, protocol
#~ from twisted.internet import defer
from twisted.internet.protocol import Factory, Protocol

# PIL
from PIL import Image

#std stuff
import sys, struct, time

#local
import rfb

class FramerateCalculator(object):

    def __init__(self, smoothing=0.9):
        self._smoothing = smoothing
        self._last_frame = None
        self.framerate = None

    def increment(self):
        if self._last_frame is not None:
            delta = time.time() - self._last_frame
            if not self.framerate:
                self.framerate = 1.0 / delta
            self.framerate = (self.framerate * self._smoothing) + ( (1.0 / delta) * (1.0 - self._smoothing))
        self._last_frame = time.time()

class RFBToGUI(rfb.RFBClient):
    """RFBClient protocol that talks to the GUI app"""

    def vncConnectionMade(self):
        """choose appropriate color depth, resize screen"""
        self.setEncodings(self.factory.encodings)
        self.setPixelFormat()           #set up pixel format to 32 bits
        self.framebufferUpdateRequest() #request initial screen update

        self.full_fb = []
        for x in xrange(self.width):
            self.full_fb.append([(0, 0, 0) for y in xrange(self.height)])

        blank_data = "\x00" * (4 * self.width * self.height)
        self.full_fb = Image.new('RGB', (self.width, self.height))

        self.ft = self.factory.ft

        self.framerate = FramerateCalculator()
        self.last_framerate_time = time.time()

        # Clear the FT to start
        for y in xrange(0, 35):
            for x in xrange(0, 45):
                self.ft.set(x, y, (0, 0, 0))
        self.ft.show()

    def vncRequestPassword(self):
        if self.factory.password is not None:
            self.sendPassword(self.factory.password)
    
    def beginUpdate(self):
        """begin series of display updates"""
        pass

    def commitUpdate(self, rectangles = None):
        """finish series of display updates"""
        self.framebufferUpdateRequest(incremental=1)
        img = self.full_fb.resize( (self.ft.width, self.ft.height), resample=Image.BILINEAR )
        for x in xrange(0, self.ft.width):
            for y in xrange(0, self.ft.height):
                r, g, b = img.getpixel( (x, y) )
                self.ft.set(x, y, (r, g, b))
        self.ft.show()
        self.framerate.increment()
        delta = time.time() - self.last_framerate_time
        if self.framerate.framerate is not None and delta > SHOW_FRAMERATE_EVERY:
            print "Framerate: %.01f" % self.framerate.framerate
            self.last_framerate_time = time.time()

    def updateRectangle(self, x, y, width, height, data):
        """new bitmap data"""
        img = Image.frombytes('RGBA', (width, height), data)     #TODO color format
        #~ log.msg("screen update")

        self.full_fb.paste(
            img,
            (x, y)
        )

    def copyRectangle(self, srcx, srcy, x, y, width, height):
        """copy src rectangle -> destinantion"""
        img = self.full_fb.crop( (srcx, srcy, width, height) )
        self.full_fb.paste(
            img,
            (x, y)
        )

    def fillRectangle(self, x, y, width, height, color):
        """fill rectangle with one color"""
        #~ remoteframebuffer.CopyRect(srcx, srcy, x, y, width, height)
        self.full_fb.paste(struct.unpack("BBBB", color), (x, y, width, height))

class VNCFactory(rfb.RFBFactory):
    """A factory for remote frame buffer connections."""
    
    def __init__(self, ft, depth, fast, *args, **kwargs):
        rfb.RFBFactory.__init__(self, *args, **kwargs)
        self.ft = ft
        if depth == 32:
            self.protocol = RFBToGUI
        else:
            raise ValueError, "color depth not supported"
            
        if fast:
            self.encodings = [
                rfb.COPY_RECTANGLE_ENCODING,
                rfb.RAW_ENCODING,
            ]
        else:
            self.encodings = [
                rfb.COPY_RECTANGLE_ENCODING,
                rfb.HEXTILE_ENCODING,
                rfb.CORRE_ENCODING,
                rfb.RRE_ENCODING,
                rfb.RAW_ENCODING,
            ]

    def buildProtocol(self, addr):
        display = addr.port - 5900
        return rfb.RFBFactory.buildProtocol(self, addr)

    def clientConnectionLost(self, connector, reason):
        log.msg("connection lost: %r" % reason.getErrorMessage())
        reactor.stop()

    def clientConnectionFailed(self, connector, reason):
        log.msg("cannot connect to server: %r\n" % reason.getErrorMessage())
        reactor.stop()

class Options(usage.Options):
    optParameters = [
        ['display',     'd', '0',               'VNC display'],
        ['vnchost',     'h', 'localhost',       'vnc remote hostname'],
        ['fthost',      't', 'localhost',       'flaschen taschen hostname'],
        ['ftport',      None, 1337,              'flaschen taschen port'],
        ['width',       None, 45,                'flaschen taschen width'],
        ['height',      None, 35,                'flaschen taschen height'],
        ['layer',       None, 0,                'flaschen taschen layer'],
        ['outfile',     'o', None,              'Logfile [default: sys.stdout]'],
        ['password',    'p', None,              'VNC password'],
        ['depth',       'D', '32',              'Color depth'],
    ]
    optFlags = [
        ['shared',      's',                    'Request shared session'],
        ['fast',        'f',                    'Fast connection is used'],
    ]

def main():
    o = Options()
    try:
        o.parseOptions()
    except usage.UsageError, errortext:
        print "%s: %s" % (sys.argv[0], errortext)
        print "%s: Try --help for usage details." % (sys.argv[0])
        raise SystemExit, 1

    depth = int(o.opts['depth'])

    logFile = sys.stdout
    if o.opts['outfile']:
        logFile = o.opts['outfile']
    log.startLogging(logFile)
    
    host = o.opts['vnchost']
    display = int(o.opts['display'])
    if host is None:
        if host == '':
            raise SystemExit
        if ':' in host:
            host, display = host.split(':')
            if host == '':  host = 'localhost'
            display = int(display)

    ft = flaschen.Flaschen(o.opts['fthost'],
                           o.opts['ftport'],
                           o.opts['width'],
                           o.opts['height'],
                           int(o.opts['layer']))

    # connect to this host and port, and reconnect if we get disconnected
    reactor.connectTCP(
        host,                                   #remote hostname
        display + 5900,                         #TCP port number
        VNCFactory(
                ft,
                depth,                          #color depth
                o.opts['fast'],                 #if a fast connection is used
                o.opts['password'],             #password or none
                int(o.opts['shared']),          #shared session flag
        )
    )

    # run the application
    reactor.run()


if __name__ == '__main__':
    main()
