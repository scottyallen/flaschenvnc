#!/usr/bin/env python
"""
Python VNC Viewer
PyGame version
(C) 2003 <cliechti@gmx.net>

MIT License
"""

#FLASCHEN_HOST = 'ft.noise'
FLASCHEN_HOST = 'localhost'
FLASCHEN_PORT = 1337
FLASCHEN_WIDTH = 45
FLASCHEN_HEIGHT = 35
FLASCHEN_LAYER = 1

import flaschen

#twisted modules
from twisted.python import usage, log
from twisted.internet import reactor, protocol
#~ from twisted.internet import defer
from twisted.internet.protocol import Factory, Protocol

#import pygame stuff
import pygame
from pygame.locals import *

#std stuff
import sys, struct

#local
import rfb

#~ class PyGameApp(pb.Referenceable, Game.Game):
class PyGameApp:
    """Pygame main application"""
    
    def __init__(self):
        width, height = 640, 480
        self.setRFBSize(width, height)
        pygame.display.set_caption('Python VNC Viewer')
        self.clock = pygame.time.Clock()
        self.alive = 1
        self.loopcounter = 0
        self.sprites = pygame.sprite.RenderUpdates()
        self.buttons = 0
        self.protocol = None
        
    def setRFBSize(self, width, height, depth=32):
        """change screen size"""
        self.width, self.height = width, height
        self.area = Rect(0, 0, width, height)
        winstyle = 0  # |FULLSCREEN
        if depth == 32:
            self.screen = pygame.display.set_mode(self.area.size, winstyle, 32)
        else:
            raise ValueError, "color depth not supported"
        self.background = pygame.Surface((self.width, self.height), depth)
        self.background.fill(0) #black

    def setProtocol(self, protocol):
        """attach a protocol instance to post the events to"""
        self.protocol = protocol

    def checkEvents(self):
        """process events from the queue"""
        seen_events = 0
        for e in pygame.event.get():
            seen_events = 1
            #~ print e
            if e.type == QUIT:
                self.alive = 0
                reactor.stop()
            if self.protocol is not None:
              pass
            return not seen_events
        return not seen_events

    def mainloop(self, dum=None):
        """gui 'mainloop', it is called repeated by twisteds mainloop 
           by using callLater"""
        no_work = self.checkEvents()

        if self.alive:
            reactor.callLater(no_work and 0.020, self.mainloop)



class RFBToGUI(rfb.RFBClient):
    """RFBClient protocol that talks to the GUI app"""

    def vncConnectionMade(self):
        """choose appropriate color depth, resize screen"""
        self.remoteframebuffer = self.factory.remoteframebuffer
        self.screen = self.remoteframebuffer.screen
        self.remoteframebuffer.setProtocol(self)
        self.remoteframebuffer.setRFBSize(self.width, self.height, 32)
        self.setEncodings(self.factory.encodings)
        self.setPixelFormat()           #set up pixel format to 32 bits
        self.framebufferUpdateRequest() #request initial screen update

        self.full_fb = []
        for x in xrange(self.width):
          self.full_fb.append([(0, 0, 0) for y in xrange(self.height)])

        blank_data = "\x00" * (4 * self.width * self.height)
        self.full_fb = pygame.image.frombuffer(blank_data, (self.width, self.height), 'RGBX')

        self.ft = flaschen.Flaschen(FLASCHEN_HOST,
                                    FLASCHEN_PORT,
                                    FLASCHEN_WIDTH,
                                    FLASCHEN_HEIGHT,
                                    FLASCHEN_LAYER)
        for y in xrange(0, 35):
          for x in xrange(0, 45):
            self.ft.set(x, y, (0, 0, 0))
        self.ft.show()

    def vncRequestPassword(self):
        if self.factory.password is not None:
            self.sendPassword(self.factory.password)
        else:
            #XXX hack, this is blocking twisted!!!!!!!
            screen = pygame.display.set_mode((220,40))
            screen.fill((255,100,0)) #redish bg
    
    def beginUpdate(self):
        """begin series of display updates"""
        pass

    def commitUpdate(self, rectangles = None):
        """finish series of display updates"""
        pygame.display.update(rectangles)
        self.framebufferUpdateRequest(incremental=1)
        img = pygame.transform.smoothscale(self.full_fb, (FLASCHEN_WIDTH, FLASCHEN_HEIGHT))
        for x in xrange(0, FLASCHEN_WIDTH):
          for y in xrange(0, FLASCHEN_HEIGHT):
            r, g, b, _ = img.get_at( (x, y) )
            self.ft.set(x, y, (r, g, b))
        self.ft.show()

    def updateRectangle(self, x, y, width, height, data):
        """new bitmap data"""
        #~ print "%s " * 5 % (x, y, width, height, len(data))
        img = pygame.image.fromstring(data, (width, height), 'RGBX')     #TODO color format
        #~ log.msg("screen update")
        self.screen.blit(
            img,
            (x, y)
        )

        self.full_fb.blit(
            img,
            (x, y)
        )

    def copyRectangle(self, srcx, srcy, x, y, width, height):
        """copy src rectangle -> destinantion"""
        #~ print "copyrect", (srcx, srcy, x, y, width, height)
        self.screen.blit(self.screen,
            (x, y),
            (srcx, srcy, width, height)
        )

        self.full_fb.blit(self.full_fb,
            (x, y),
            (srcx, srcy, width, height)
        )

    def fillRectangle(self, x, y, width, height, color):
        """fill rectangle with one color"""
        #~ remoteframebuffer.CopyRect(srcx, srcy, x, y, width, height)
        self.screen.fill(struct.unpack("BBBB", color), (x, y, width, height))
        self.full_fb.fill(struct.unpack("BBBB", color), (x, y, width, height))

    def bell(self):
        print "katsching"

    def copy_text(self, text):
        print "Clipboard: %r" % text

class VNCFactory(rfb.RFBFactory):
    """A factory for remote frame buffer connections."""
    
    def __init__(self, remoteframebuffer, depth, fast, *args, **kwargs):
        rfb.RFBFactory.__init__(self, *args, **kwargs)
        self.remoteframebuffer = remoteframebuffer
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
        pygame.display.set_caption('Python VNC Viewer on %s:%s' % (addr.host, display))
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
        ['host',        'h', None,              'remote hostname'],
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
    
    pygame.init()
    remoteframebuffer = PyGameApp()
    
    host = o.opts['host']
    display = int(o.opts['display'])
    if host is None:
        screen = pygame.display.set_mode((220,40))
        screen.fill((0,100,255)) #blue bg
        #host = inputbox.ask(screen, "Host")
        if host == '':
            raise SystemExit
        if ':' in host:
            host, display = host.split(':')
            if host == '':  host = 'localhost'
            display = int(display)

    # connect to this host and port, and reconnect if we get disconnected
    reactor.connectTCP(
        host,                                   #remote hostname
        display + 5900,                         #TCP port number
        VNCFactory(
                remoteframebuffer,              #the application/display
                depth,                          #color depth
                o.opts['fast'],                 #if a fast connection is used
                o.opts['password'],             #password or none
                int(o.opts['shared']),          #shared session flag
        )
    )

    # run the application
    reactor.callLater(0.1, remoteframebuffer.mainloop)
    reactor.run()


if __name__ == '__main__':
    main()
