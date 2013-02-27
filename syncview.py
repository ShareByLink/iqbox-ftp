import sys
import signal

from PySide.QtCore import Qt
from PySide.QtGui import QWidget, QMainWindow, QApplication
from PySide.QtGui import QPushButton, QLabel, QLineEdit, QFont
from PySide.QtGui import QHBoxLayout, QVBoxLayout, QPixmap, QFrame

class SyncWindow(QMainWindow):
    
    def __init__(self, parent=None):
        super(SyncWindow, self).__init__(parent)
        
        self.setStyleSheet('SyncWindow {background: white}')
        self.setWindowTitle('FTPSync')
        self.loginView()
        
    def loginView(self):
        login = LoginView()
        
        
        self.setCentralWidget(login)
        self.setFixedSize(login.size())


class LoginView(QWidget):
    
    def __init__(self, parent=None):
        super(LoginView, self).__init__(parent)
        
        self.createWidgets()
        self.createLayouts()
        self.setFixedSize(250, 325)
        
    def createLayouts(self):
        mainLayout = QHBoxLayout()
        fieldsLayout = QVBoxLayout()
        
        mainLayout.addStretch(20)
        
        fieldsLayout.addStretch(10)
        fieldsLayout.addWidget(self.iconLabel)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine);
        line.setFrameShadow(QFrame.Sunken);
        
        fieldsLayout.addWidget(line)
        fieldsLayout.addStretch(20)
        fieldsLayout.addWidget(self.hostLabel)
        fieldsLayout.addWidget(self.hostEdit)
        fieldsLayout.addWidget(self.usernameLabel)
        fieldsLayout.addWidget(self.usernameEdit)
        fieldsLayout.addWidget(self.passwdLabel)
        fieldsLayout.addWidget(self.passwdEdit)
        fieldsLayout.addStretch(30)
        
        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(50)
        buttonLayout.addWidget(self.loginButton, 50, Qt.AlignRight)
        
        fieldsLayout.addLayout(buttonLayout)
        fieldsLayout.addStretch(20)
        
        mainLayout.addLayout(fieldsLayout, 30)
        mainLayout.addStretch(20)
        
        self.setLayout(mainLayout)
        
    def createWidgets(self):
        fieldsWidth = 200
        labelsFont = QApplication.font()
        labelsFont.setBold(True)
        
        self.iconLabel = QLabel(self)
        self.iconLabel.setPixmap(QPixmap('logo.png'))
        
        self.hostLabel = QLabel(self)
        self.hostEdit = QLineEdit(self)
        self.hostLabel.setText('FTP Location')
        self.hostLabel.setFont(labelsFont)
        self.hostEdit.setFixedWidth(fieldsWidth)
        
        self.usernameLabel = QLabel(self)
        self.usernameEdit = QLineEdit(self)
        self.usernameLabel.setText('Username')
        self.usernameLabel.setFont(labelsFont)
        self.usernameEdit.setFixedWidth(fieldsWidth)
        
        self.passwdLabel = QLabel(self)
        self.passwdEdit = QLineEdit(self)
        self.passwdLabel.setText('Password')
        self.passwdLabel.setFont(labelsFont)
        self.passwdEdit.setFixedWidth(fieldsWidth)
        self.passwdEdit.setEchoMode(QLineEdit.Password)
        
        self.loginButton = QPushButton(self)
        self.loginButton.setText('Login')
        self.loginButton.setFont(labelsFont)
        self.loginButton.setFixedWidth(fieldsWidth / 2)
        self.loginButton.setStyleSheet('')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SyncWindow()
    font = QFont('', -1, 50, False)
    
    app.setFont(font)
    window.show()
    sys.exit(app.exec_())
