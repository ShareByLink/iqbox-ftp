import os
import sys
import platform
import traceback

from PySide.QtCore import Qt, Slot, Signal, QSettings, QDir, QThread, QTimer
from PySide.QtGui import QWidget, QMainWindow, QApplication, QCheckBox
from PySide.QtGui import QPushButton, QLabel, QLineEdit, QFont, QFileDialog, QMessageBox
from PySide.QtGui import QHBoxLayout, QVBoxLayout, QPixmap, QFrame, QIcon, QSystemTrayIcon

import resources
import syncapp


resources.qInitResources()

# To be used with the `QSettings` objects 
SettingsKeys = {
    'host': 'Host',
    'username': 'Username',
    'passwd': 'Password',
    'localdir': 'LocalDir',
    'ssl': 'SSL'}

# Selecting a good font family for each platform
osname = platform.system()
if osname == 'Windows':
    fontfamily = 'Segoe UI'
elif osname == 'Linux':
    fontfamily = ''
else:
    fontfamily = '' 


def get_settings():
    """
    Creates a `QSettings` object set up for the application.
    Returns a `QSettings` object.
    """
    
    return QSettings('IQStorage', 'FTPSync')


class SyncWindow(QMainWindow):
    """
    Applications main window. This class is meant to handle
    every widget needed by the application, as well as other
    needed global objects and behavior.
    """
    
    failedLogIn = Signal()
    doCheckout = Signal((bool,))
    
    def __init__(self, parent=None):
        super(SyncWindow, self).__init__(parent)
        
        # Sets up several UI aspects
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(QPixmap(':/resources/icon.png')))
        self.tray.show()
        
        self.setStyleSheet('SyncWindow {background: white}')
        self.setWindowTitle('FTPSync')
        self.setWindowIcon(QIcon(QPixmap(':/resources/logobar.png')))
        self.statusBar().setFont(View.labelsFont())
        self.ftpThread = None
        
        # Initializes the window with a `LoginView` widget.
        self.loginView()
        
    def loginView(self):
        """
        Initializes a `LoginView` object and sets it up as the main window's
        central widget.
        """
        
        login = LoginView()
        
        login.login.connect(self.onLogin)
        self.failedLogIn.connect(login.onFailedLogIn)
        
        self.setCentralWidget(login)
        self.setFixedSize(login.size())
        self.statusBar().hide()
        
    def syncView(self):
        """
        Initializes a `SyncView` object and sets it up as the main window's
        central widget.
        """        
        
        syncview = SyncView()
        
        self.setCentralWidget(syncview)
        self.setFixedSize(syncview.size())
        self.statusBar().show()
        
        syncview.sync.connect(self.onSync)
        
    def getFtp(self, host, ssl):
        """
        Creates an FTP object to be used by the application.
        
        :param host: Indicates the hostname of the FTP server
        :param ssl: Indicates whether the FTP needs SSL support
        """
        
        self.ftpThread = QThread()
        sync = syncapp.FtpObject(host, ssl)
        
        sync.downloadProgress.connect(self.onDownloadProgress)
        sync.downloadingFile.connect(self.onDownloadingFile)
        sync.checkoutDone.connect(self.onCheckoutDone)
        self.doCheckout.connect(sync.checkout)
        QApplication.instance().lastWindowClosed.connect(self.ftpThread.quit)
        
        sync.moveToThread(self.ftpThread)
        self.ftpThread.start()
        
        return sync
   
    @Slot(str, str, str, bool)
    def onLogin(self, host, username, passwd, ssl):
        """
        Slot. Triggers a log in request to the server.
        
        :param host: Indicates the hostname of the FTP server
        :param username: Username to log in into the FTP server
        :param passwd: Password to log in into the FTP server
        :param ssl: Indicates whether the FTP needs SSL support
        """
        
        self.sync = self.getFtp(host, ssl)
        
        try:
            loginResponse = self.sync.ftp.login(username, passwd)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            
            warning = QMessageBox(self)
            warning.setFont(View.labelsFont())
            warning.setStyleSheet('QMessageBox {background: white}')
            warning.setWindowTitle("Error")
            warning.setText(
                "Log in failed.\nPlease check your credentials and SSL settings.")
            warning.setIcon(QMessageBox.Warning)
            warning.addButton("Ok", QMessageBox.AcceptRole).setFont(View.editsFont())
            warning.exec_()
            
            self.failedLogIn.emit()
        else:
            print loginResponse
            if '230' in loginResponse:
                # 230 in server response is good! Change current view
                self.syncView()
            else:
                self.failedLogIn.emit()
                
    @Slot(str)
    def onSync(self, localdir):
        """
        Slot. Triggers a server checkout.
        
        :param localdir: Absolute local directory path where to keep the files
        """
        
        self.sync.setLocalDir(localdir)
        self.doCheckout.emit(True)

    @Slot(int, int)
    def onDownloadProgress(self, total, progress):
        """
        Slot. Triggers download progress update in the UI.
        
        :param total: Total size of the download in bytes
        :param progress: Current downdload progress in bytes
        """
        
        if progress <= 0:
            return
        else:
            percent = (progress * 100) / total
            self.statusBar().showMessage('%s %d%%' % (self.currentFile, percent))
        
    @Slot(str)
    def onDownloadingFile(self, filename):
        """
        Slot. Updates the current download filename to be used in the UI
        
        :param filename: Name of the file that is being downloaded
        """
        
        self.currentFile = filename
    
    @Slot()
    def onCheckoutDone(self):
        """
        Slot. Will be called when the application finished syncing 
        with the FTP server.
        """
        
        self.statusBar().showMessage('Sync completed')
        QTimer.singleShot(5000, self.clearMessage)
        
    @Slot()
    def clearMessage(self):
        self.statusBar().showMessage('')

class View(QWidget):
    """Base `View` class. Defines behavior common in all views"""
    
    def __init__(self, parent=None):
        """
        Init method. Initializes parent classes
        
        :param parent: Reference to a `QWidget` object to be used as parent 
        """
        
        super(View, self).__init__(parent)
        
    @staticmethod
    def labelsFont():
        """Returns the `QFont` that `QLabels` should use"""
        
        return View.font(True)
        
    @staticmethod
    def editsFont():
        """Returns the `QFont` that `QLineEdits` should use"""
        
        return View.font(False)
        
    @staticmethod
    def font(bold):
        """
        Returns a `QFont` object to be used in `View` derived classes.
        
        :param bold: Indicates whether or not the font will be bold
        """
         
        font = QFont(fontfamily, 9, 50, False)
        font.setBold(bold)
        
        return font
        
    def setLogo(self):
        """Sets the company logo in the same place in all views"""
        
        logoPixmap = QPixmap(':/resources/logo.png')
        self.iconLabel = QLabel(self)
        self.iconLabel.setPixmap(logoPixmap)
        self.iconLabel.setGeometry(20, 20, logoPixmap.width(), logoPixmap.height())
        
        # Defines a visual line separator to be placed under the `logoPixmap` `QLabel`
        self.line = QFrame()
        self.line.setFrameShape(QFrame.HLine);
        self.line.setFrameShadow(QFrame.Sunken);


class LoginView(View):
    """`View` derived class. Defines the log in widget"""
    
    login = Signal((str, str, str, bool,))
    
    def __init__(self, parent=None):
        """
        Init method. Initializes parent classes
        
        :param parent: Reference to a `QWidget` object to be used as parent 
        """
        
        super(LoginView, self).__init__(parent)
        
        self.createWidgets()
        self.createLayouts()
        self.setFixedSize(250, 325)
        
    def createLayouts(self):
        """Put widgets into layouts, thus creating the widget"""
        
        mainLayout = QHBoxLayout()
        fieldsLayout = QVBoxLayout()
        ftpInfoLayout = QHBoxLayout()
        buttonLayout = QHBoxLayout()
        
        mainLayout.addStretch(20)
        
        fieldsLayout.addStretch(80)
        fieldsLayout.addWidget(self.line)
        fieldsLayout.addStretch(20)
        
        ftpInfoLayout.addWidget(self.hostLabel, 50, Qt.AlignLeft)
        ftpInfoLayout.addStretch(20)
        ftpInfoLayout.addWidget(self.sslLabel, 20, Qt.AlignRight)
        ftpInfoLayout.addWidget(self.sslCheck, 10, Qt.AlignRight)
        
        fieldsLayout.addLayout(ftpInfoLayout)
        fieldsLayout.addWidget(self.hostEdit)
        fieldsLayout.addWidget(self.usernameLabel)
        fieldsLayout.addWidget(self.usernameEdit)
        fieldsLayout.addWidget(self.passwdLabel)
        fieldsLayout.addWidget(self.passwdEdit)
        fieldsLayout.addStretch(30)
        
        buttonLayout.addStretch(50)
        buttonLayout.addWidget(self.loginButton, 50, Qt.AlignRight)
        
        fieldsLayout.addLayout(buttonLayout)
        fieldsLayout.addStretch(20)
        
        mainLayout.addLayout(fieldsLayout, 30)
        mainLayout.addStretch(20)
        
        self.setLayout(mainLayout)
        
    def createWidgets(self):
        """Create children widgets needed by this view"""

        fieldsWidth = 200
        labelsFont = View.labelsFont()
        editsFont = View.editsFont()
        self.setLogo()
        
        self.hostLabel = QLabel(self)
        self.hostEdit = QLineEdit(self)
        self.sslLabel = QLabel(self)
        self.sslCheck = QCheckBox(self)     
        self.hostLabel.setText('FTP Location')
        self.hostLabel.setFont(labelsFont)
        self.hostEdit.setFixedWidth(fieldsWidth)
        self.hostEdit.setFont(editsFont)
        self.sslLabel.setText('SSL')
        self.sslLabel.setFont(labelsFont)
        
        self.usernameLabel = QLabel(self)
        self.usernameEdit = QLineEdit(self)
        self.usernameLabel.setText('Username')
        self.usernameLabel.setFont(labelsFont)
        self.usernameEdit.setFixedWidth(fieldsWidth)
        self.usernameEdit.setFont(editsFont)
        
        self.passwdLabel = QLabel(self)
        self.passwdEdit = QLineEdit(self)
        self.passwdLabel.setText('Password')
        self.passwdLabel.setFont(labelsFont)
        self.passwdEdit.setFixedWidth(fieldsWidth)
        self.passwdEdit.setEchoMode(QLineEdit.Password)
        self.passwdEdit.setFont(editsFont)
        self.passwdEdit.returnPressed.connect(self.onLoginClicked)
        
        self.loginButton = QPushButton(self)
        self.loginButton.setText('Login')
        self.loginButton.setFont(labelsFont)
        self.loginButton.setFixedWidth(fieldsWidth / 2)
        self.loginButton.clicked.connect(self.onLoginClicked)
        
        # Sets previously stored values into the fields, if any
        settings = get_settings()
        
        self.hostEdit.setText(settings.value(SettingsKeys['host'], ''))
        self.usernameEdit.setText(settings.value(SettingsKeys['username'], ''))
        self.passwdEdit.setText(settings.value(SettingsKeys['passwd'], ''))
        
        # Unicode to boolean conversion
        ssl = settings.value(SettingsKeys['ssl'], u'true') 
        ssl = True if ssl == u'true' else False
        self.sslCheck.setChecked(ssl)
        
    @Slot() 
    def onLoginClicked(self):
        """
        Slot. Called on the user clicks on the `loginButton` button
        """
        
        # Takes out the user input from the fields
        host = self.hostEdit.text()
        username = self.usernameEdit.text()
        passwd = self.passwdEdit.text()
        ssl = self.sslCheck.isChecked()
        
        print 'Logging in: %s, %s, %s' % (host, username, passwd)
        
        if len(host) > 0:
            # If the fields are valid, store them using a `QSettings` object
            # and triggers a log in request
            settings = get_settings()
            
            settings.setValue(SettingsKeys['host'], host)
            settings.setValue(SettingsKeys['username'], username)
            settings.setValue(SettingsKeys['passwd'], passwd)
            settings.setValue(SettingsKeys['ssl'], ssl)
            
            self.setEnabled(False)
            self.login.emit(host.strip(), username, passwd, ssl)
            
    @Slot()
    def onFailedLogIn(self):
        """
        Slot. Called when the log in request fails
        """
        
        # Enables the fields again for user input
        self.setEnabled(True)
        
        
class SyncView(View):
    """`View` derived class. Defines the sync widget"""
    sync = Signal((str,))
    
    def __init__(self, parent=None):
        """
        Init method. Initializes parent classes
        
        :param parent: Reference to a `QWidget` object to be used as parent 
        """
        super(SyncView, self).__init__(parent)
        
        self.createWidgets()
        self.createLayouts()
        self.setFixedSize(580, 325)

    def createLayouts(self):
        """Put widgets into layouts, thus creating the widget"""
        
        mainLayout = QHBoxLayout()
        fieldsLayout = QVBoxLayout()
        pathLayout = QHBoxLayout()
        buttonLayout = QHBoxLayout()
        
        mainLayout.addStretch(10)
        
        fieldsLayout.addStretch(50)
        fieldsLayout.addWidget(self.line)
        
        fieldsLayout.addWidget(self.localdirLabel) 
        pathLayout.addWidget(self.localdirEdit)
        pathLayout.addWidget(self.browseButton)
        fieldsLayout.addLayout(pathLayout)
        
        buttonLayout.addStretch(50)
        buttonLayout.addWidget(self.syncButton, 50, Qt.AlignRight)
        
        fieldsLayout.addLayout(buttonLayout)
        fieldsLayout.addStretch(100)

        mainLayout.addLayout(fieldsLayout, 60)
        mainLayout.addStretch(10)
        
        self.setLayout(mainLayout)
        
    def createWidgets(self):
        """Create children widgets needed by this view"""
        
        fieldsWidth = 450
        labelsFont = View.labelsFont()
        editsFont = View.editsFont()
        
        self.setLogo()
        
        self.localdirLabel = QLabel(self)
        self.localdirEdit = QLineEdit(self)
        self.localdirLabel.setText('Choose a directory')
        self.localdirLabel.setFont(labelsFont)
        self.localdirEdit.setFixedWidth(fieldsWidth)
        self.localdirEdit.setReadOnly(True)
        self.localdirEdit.setFont(editsFont)
        
        self.browseButton = QPushButton(self)
        self.browseButton.setText('Browse')
        self.browseButton.setFont(labelsFont)
        
        self.syncButton = QPushButton(self)
        self.syncButton.setText('Sync')
        self.syncButton.setFont(labelsFont)
        
        self.browseButton.clicked.connect(self.onBrowseClicked)
        self.syncButton.clicked.connect(self.onSyncClicked)
        
        settings = get_settings()
        self.localdirEdit.setText(settings.value(SettingsKeys['localdir'], ''))
        
    @Slot()
    def onBrowseClicked(self):
        """Slot. Called when the user clicks on the `browseButton` button"""
        
        # Presents the user with a native directory selector window
        localdir = QFileDialog.getExistingDirectory()
        localdir = QDir.fromNativeSeparators(localdir)
        if len(localdir) > 0:
            # If `localdir`'s value is good, store it using a `QSettings` object
            # and triggers a sync request.
            # Careful with '\' separators on Windows.
            if not localdir.endswith('FTPSync'):
                localdir = os.path.join(localdir, 'FTPSync')
            localdir = QDir.toNativeSeparators(localdir)
            get_settings().setValue(SettingsKeys['localdir'], localdir)
            self.localdirEdit.setText(localdir)
            
    @Slot()
    def onSyncClicked(self):
        """Slot. Called when the user clicks on the `syncButton` button"""
    
        localdir = self.localdirEdit.text()
        if len(localdir) > 0:
            self.sync.emit(localdir)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = SyncWindow()
    font = QFont(fontfamily, 12, 50, False)
    
    app.setFont(font)
    window.show()
    sys.exit(app.exec_())
