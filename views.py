import platform

from PySide.QtGui import (
      QWidget, QPixmap, QLabel, QFont, QFrame, QPushButton, QPainter, QBrush,
      QColor, QLineEdit, QHBoxLayout, QVBoxLayout, QCheckBox, QFileDialog)
from PySide.QtCore import Signal, Slot, QDir, Qt

from localsettings import get_settings, SettingsKeys
import crypt


class View(QWidget):
    """Base `View` class. Defines behavior common in all views"""
    # Selecting a good font family for each platform
    osname = platform.system()
    if osname == 'Windows':
        fontFamily = 'Segoe UI'
    elif osname == 'Linux':
        fontFamily = ''
    else:
        fontFamily = ''
    
    
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
        
        font = QFont(View.fontFamily, 9, 50, False)
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
        self.passwdEdit.setText(crypt.decrypt(settings.value(SettingsKeys['passwd'], '')))
        
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
        
        print 'Logging in: %s, %s, %s' % (host, username, '*' * len(passwd))
        
        if len(host) > 0:
            # If the fields are valid, store them using a `QSettings` object
            # and triggers a log in request
            settings = get_settings()
            
            settings.setValue(SettingsKeys['host'], host)
            settings.setValue(SettingsKeys['username'], username)
            settings.setValue(SettingsKeys['passwd'], crypt.encrypt(passwd))
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

        self.status.setMessage('Ready')

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
        fieldsLayout.addStretch(10)
        fieldsLayout.addWidget(self.statusLabel)
        fieldsLayout.addWidget(self.status)
        fieldsLayout.addStretch(80)

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
        self.localdirLabel.setText('Choose a folder')
        self.localdirLabel.setFont(labelsFont)
        self.localdirEdit.setFixedWidth(fieldsWidth)
        self.localdirEdit.setReadOnly(False)
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
        
        self.statusLabel = QLabel(self)
        self.statusLabel.setText('Status')
        self.statusLabel.setFont(View.labelsFont())
        self.status = StatusArea(self)

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
            localdir = QDir.toNativeSeparators(localdir)
            get_settings().setValue(SettingsKeys['localdir'], localdir)
            self.localdirEdit.setText(localdir)
            
    @Slot()
    def onSyncClicked(self):
        """Slot. Called when the user clicks on the `syncButton` button"""
    
        localdir = self.localdirEdit.text()
        if len(localdir) > 0:
            self.syncButton.setEnabled(False)
            self.sync.emit(localdir)


class StatusArea(QWidget):
    def __init__(self, parent=None):
        super(StatusArea, self).__init__(parent)
        self.setStyleSheet('StatusArea {background: yellow}')
        self.msg = QLabel(self)
        self.file = QLabel(self)
        self.progress = QLabel(self)
   
        self.msg.setFont(View.labelsFont())
        self.file.setFont(View.editsFont())
        self.progress.setFont(View.labelsFont())

        layout = QHBoxLayout()
        layout.addWidget(self.msg, 0, Qt.AlignLeft)
        layout.addWidget(self.file, 0, Qt.AlignLeft)
        layout.addWidget(self.progress, 0, Qt.AlignRight)

        self.setLayout(layout)

    @Slot(str)
    @Slot(str, str, str)
    def setMessage(self, msg, file='', progress=None):
        progress = '{}%'.format(progress) if progress else '' 
        self.msg.setText(msg)
        self.file.setText(file)
        self.progress.setText(progress)

    def paintEvent(self, event):
        p = QPainter()
        p.begin(self)
        p.fillRect(self.rect(), QBrush(QColor(240, 200, 0)))
        p.end()
