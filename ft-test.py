import flaschen

UDP_IP = 'ft.noise'
UDP_PORT = 1337

ft = flaschen.Flaschen(UDP_IP, UDP_PORT, 45, 35)

for y in xrange(0, 35):
  for x in xrange(0, 45):
    ft.set(x, y, (0, 0, 255))
ft.show()
