import socket

class Flaschen(object):
  def __init__(self, host, port, width, height):
    self.host = host
    self.port = port
    self.pixels = []
    for x in xrange(width):
      self.pixels.append([(0, 0, 0) for y in xrange(height)])
    self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

  def send(self, data):
    self.sock.sendto(data, (self.host, self.port))

  def header(self):
    return ''.join(["P6\n",
                    "45 35\n",
                    "255\n"])

  def footer(self):
    return ''.join(["0\n",
                    "0\n",
                    "14\n"])

  def set(self, x, y, c):
    self.pixels[x][y] = c
  
  def show(self):
    data = []
    for y in xrange(0, 35):
      for x in xrange(0, 45):
        data.append(''.join([chr(c) for c in self.pixels[x][y]]))

    print self.header() + ''.join(data) + "\n" + self.footer()
    self.send(self.header() + ''.join(data) + "\n" + self.footer())
