import sys
import sqlalchemy
from PySide import QtGui

print 'SQL Alchemy Version: '
print sqlalchemy.__version__


app = QtGui.QApplication(sys.argv)

wid = QtGui.QWidget()
wid.resize(250, 150)
wid.setWindowTitle('Simple')
wid.show()

sys.exit(app.exec_())