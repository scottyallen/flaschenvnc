VNC to Flaschen Taschen bridge

Requires Twisted and PIL

To install:

  pip install -r requirements.txt

Usage:

  python flaschenvnc.py -h 127.0.0.1 -p 'password'

Note:

On OSX, if you're using the builtin VNC server (which you can turn on in System Preferences -> Sharing ->
Screen Sharing) you need to run the following to allow you to log in directly to the currently logged in user:

  sudo defaults write /Library/Preferences/com.apple.RemoteManagement VNCAlwaysStartOnConsole -bool true

More info on Flaschen Taschen: https://github.com/hzeller/flaschen-taschen

Based on code by Chris Liechti: http://homepage.hispeed.ch/py430/python/
MIT License
