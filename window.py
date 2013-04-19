import os
import sys
import platform
import traceback
from datetime import datetime as dt

from PySide.QtCore import Qt, Slot, Signal, QSettings, QDir, QThread, QTimer
from PySide.QtGui import (
      QMainWindow, QApplication,
      QMessageBox, QIcon, QSystemTrayIcon, QPixmap)

import resources
from sync import Sync
from views import SyncView, LoginView, View
from localsettings import get_settings, SettingsKeys


resources.qInitResources()


class SyncWindow(QMainWindow):
    """
    Application main window. This class is meant to handle
    every widget needed by the application, as well as other
    needed global objects and behavior.
    """
    
    failedLogIn = Signal()
    syncStarted = Signal()
    loginRequested = Signal((str, str,))
    
    def __init__(self, parent=None):
        super(SyncWindow, self).__init__(parent)
        
        # Sets up several UI aspects
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(QIcon(QPixmap(':/resources/icon.png')))
        self.tray.show()
        
        self.setStyleSheet('SyncWindow {background: white}')
        self.setWindowTitle('IQBox')
        self.setWindowIcon(QIcon(QPixmap(':/resources/logobar.png')))
        self.statusBar().setFont(View.labelsFont())
        self.syncThread = None
        
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
        
    def getSync(self, host, ssl):
        """
        Creates a `Sync` object to be used by the application.
        
        :param host: Indicates the hostname of the FTP server
        :param ssl: Indicates whether the FTP needs SSL support
        """
        
         
    @Slot(str, str, str, bool)
    def onLogin(self, host, username, passwd, ssl):
        """
        Slot. Triggers a log in request to the server.
        
        :param host: Indicates the hostname of the FTP server
        :param username: Username to log in into the FTP server
        :param passwd: Password to log in into the FTP server
        :param ssl: Indicates whether the FTP needs SSL support
        """

        self.sync = Sync(host, ssl)
        self.syncStarted.connect(self.sync.initQueue)
        self.sync.server.downloadProgress.connect(self.onDownloadProgress)
        self.sync.server.uploadProgress.connect(self.onUploadProgress)
        self.sync.server.fileEvent.connect(self.onFileEvent)
        self.sync.server.fileEventComplete.connect(self.clearMessage)
        self.sync.server.loginCompleted.connect(self.onLoginCompleted)
        self.loginRequested.connect(self.sync.server.onLogin) 

        self.syncThread = QThread()
        self.sync.moveToThread(self.syncThread)
        self.syncThread.start()
    
        QApplication.instance().lastWindowClosed.connect(self.syncThread.quit)
        self.loginRequested.emit(username, passwd)

    @Slot(bool, str)
    def onLoginCompleted(self, ok, msg):
        if not ok:
            warning = QMessageBox(self)
            warning.setFont(View.labelsFont())
            warning.setStyleSheet('QMessageBox {background: white}')
            warning.setWindowTitle("Error")
            warning.setText(msg)
            warning.setIcon(QMessageBox.Warning)
            warning.addButton("Ok", QMessageBox.AcceptRole).setFont(View.editsFont())
            warning.exec_()
            
            self.failedLogIn.emit()

        else:
            self.syncView()
                
    @Slot(str)
    def onSync(self, localdir):
        """
        Slot. Triggers a server checkout.
        
        :param localdir: Absolute local directory path where to keep the files
        """

        self.syncStarted.emit()

        
    @Slot(int, int)
    def onProgress(self, action, total, progress):
        """
        Slot. Triggers download progress update in the UI.
        
        :param total: Total size of the download in bytes
        :param progress: Current downdload progress in bytes
        """
        
        if progress <= 0:
            return
        else:
            percent = (progress * 100) / total
            self.statusBar().showMessage('%s %s %d%%' % (action, self.currentFile, percent))
        
    @Slot(int, int)
    def onDownloadProgress(self, total, progress):
        """
        Slot. Triggers upload progress update in the UI.
        
        :param total: Total size of the download in bytes
        :param progress: Current downdload progress in bytes
        """
        
        self.onProgress('Downloading', total, progress)
        
    @Slot(int, int)
    def onUploadProgress(self, total, progress):
        """
        Slot. Triggers download progress update in the UI.
        
        :param total: Total size of the download in bytes
        :param progress: Current downdload progress in bytes
        """
        
        self.onProgress('Uploading', total, progress)
        
    @Slot(str)
    def onFileEvent(self, filename):
        """
        Slot. Updates the current download filename to be used in the UI
        
        :param filename: Name of the file that is being downloaded
        """
        
        self.currentFile = filename
          
    @Slot()
    def clearMessage(self):
        self.statusBar().showMessage('')

