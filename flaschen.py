import socket

class Flaschen(object):
  def __init__(self, host, port, width, height, layer=0):
    self.host = host
    self.port = port
    self.width = width
    self.height = height
    self.layer = layer
    self.pixels = []
    for x in xrange(width):
      self.pixels.append([(0, 0, 0) for y in xrange(height)])
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  def _send(self, data):
    self.sock.sendto(data, (self.host, self.port))

  def _header(self):
    return ''.join(["P6\n",
                    "45 35\n",
                    "255\n"])

  def _footer(self):
    return ''.join(["0\n",
                    "0\n",
                    "%d\n" % self.layer])

  def set(self, x, y, color):
    if x >= self.width or y >= self.height:
      return
    if color == (0, 0, 0):
      color = (1, 1, 1)
    self.pixels[x][y] = color
  
  def show(self):
    data = []
    for y in xrange(0, 35):
      for x in xrange(0, 45):
        data.append(''.join([chr(c) for c in self.pixels[x][y]]))

    self._send(self._header() + ''.join(data) + "\n" + self._footer())
