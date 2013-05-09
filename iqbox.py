import sys
import os
from datetime import datetime as dt

from PySide.QtGui import QApplication, QFont

from localsettings import DEBUG, WEARECODING
from window import SyncWindow
from views import View

#import engine_tools


if __name__ == '__main__':

    if WEARECODING:
        try:
          os.remove('log.txt')
        except: 
          pass
        
    if not DEBUG:
       # Redirect `sys.stderr` and `sys.stdout` to a file 
       # when building for release.
       sys.stderr = sys.stdout = open('log.txt', 'a')
    f = sys.stdout
    class F():
        def write(self, data):
            if data.strip():
                # Only attach a timestamp to non whitespace prints.
                data = '{0} {1}'.format(dt.utcnow().strftime('%Y-%m-%d %H:%M:%S'), data)
            f.write(data)
            f.flush()
    sys.stderr = sys.stdout = F()
    
    app=QApplication.instance() # checks if QApplication already exists 
    if not app: # create QApplication if it doesnt exist 
        app = QApplication(sys.argv)

    window = SyncWindow()
    font = QFont(View.fontFamily, 12, 50, False)
    
    app.setFont(font)
    window.show()
    sys.exit(app.exec_())
