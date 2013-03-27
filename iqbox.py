import sys
from datetime import datetime as dt

from PySide.QtGui import QApplication, QFont

from localsettings import DEBUG
from window import SyncWindow
from views import View


if __name__ == '__main__':
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
    sys.stderr = sys.stdout = F()
    
    app = QApplication(sys.argv)
    window = SyncWindow()
    font = QFont(View.fontFamily, 12, 50, False)
    
    app.setFont(font)
    window.show()
    sys.exit(app.exec_())
