import os
import sys
from datetime import datetime as dt

from PySide.QtCore import QObject, QCoreApplication, Slot, Signal, QTimer, QDir

import syncapp
from filebase import File, Session


class FileWatcher(QObject):
    
    fileDeleted = Signal((str,str,))
    fileAdded = Signal((str,str,))
    fileChanged = Signal((str,str,))
    finishedCheck = Signal((str,))
    
    LOCATION = 'local'
    
    def __init__(self, localdir, parent=None):
        super(FileWatcher, self).__init__(parent)
        self.localdir = localdir
    
    def checkout(self, trigger_events=True):
        check_date = dt.utcnow()
        
        for item in os.walk(self.localdir):
            directory = item[0]
            subfiles = item[-1]

            for file_ in subfiles:
                localpath = os.path.join(directory, file_)
                serverpath = localpath.replace(self.localdir, '')
                serverpath = QDir.fromNativeSeparators(serverpath)
                localmdate = dt.utcfromtimestamp(os.path.getmtime(localpath))
                
                with File.fromPath(serverpath) as local_file:
                    just_added = not local_file.inlocal
                    lastmdate = local_file.localmdate
                    
                    local_file.inlocal = True
                    local_file.last_checked_local = check_date
                    local_file.localmdate = localmdate
                    
                # Emit the signals after the attributes has been set
                # and committed.
                if trigger_events is True:
                    if just_added is True:
                        self.fileAdded.emit(FileWatcher.LOCATION, serverpath)
                    elif localmdate > lastmdate:
                        self.fileChanged.emit(FileWatcher.LOCATION, serverpath)

        # Deleted files are the ones whose `last_checked_local` attribute 
        # didn't get updated in the recursive run.
        session = Session()
        deleted = session.query(File).filter(File.last_checked_local < check_date).filter(File.inlocal == True)
        for file_ in deleted:
            if trigger_events is True:
                self.fileDeleted.emit(FileWatcher.LOCATION, file_.path)
            
        session.commit()
        QTimer.singleShot(5000, self.checkout)

    @Slot(str)
    def added(self, location, serverpath):
        print 'Added:', serverpath
        
    @Slot(str)
    def changed(self, location, serverpath):
        print 'Changed:', serverpath
        
    @Slot(str)
    def deleted(self, location, serverpath):
        with File.fromPath(serverpath) as deleted:
            deleted.inlocal = False

            print 'Deleted:', serverpath


if __name__ == '__main__':
    coreapp = QCoreApplication(sys.argv)
    watcher = FileWatcher('/home/sergio/Documents/FTPSync/mareas')
    
    app = syncapp.FtpObject('ops.osop.com.pa', False)
    app.setLocalDir('/home/sergio/Documents/FTPSync/mareas')
    print app.ftp.login('mareas', 'mareas123')
    
    app.fileAdded.connect(app.added)
    app.fileChanged.connect(app.changed)
    app.fileDeleted.connect(app.deleted)
    
    watcher.fileAdded.connect(watcher.added)
    watcher.fileChanged.connect(watcher.changed)
    watcher.fileDeleted.connect(watcher.deleted)
    
    watcher.checkout()
    app.checkout(False)
    coreapp.exec_()
