import os
import sys
import traceback

from PySide.QtCore import QObject, Slot, Signal, QTimer, QDir, QThread

from dbcore import File, FileAction, ActionQueue, Session, empty_db
from watchers import ServerWatcher, LocalWatcher


class Sync(QObject):
    
    deleteServerFile = Signal((str,))
    downloadFile = Signal((str,))
    uploadFile = Signal((str,))
    checkServer = Signal()
    checkLocal = Signal()
    
    def __init__(self, host, ssl, parent=None):
        super(Sync, self).__init__(parent)

        self.server = ServerWatcher(host, ssl, self)
        
        self.preloaedActions = []
        self.doPreemptive = empty_db()
        self.connected = False
        self.firstScan = True
        
    def setLocalDir(self, localdir):
        self.local = LocalWatcher(localdir)
        self.server.setLocalDir(localdir)

        self.local.moveToThread(self.thread())
        self.local.setParent(self)
    
    def connections(self):
        if not self.connected:
            self.connected = True
            self.server.fileAdded.connect(self.onAdded)
            self.server.fileChanged.connect(self.onChanged)
            self.server.fileDeleted.connect(self.onDeleted)

            self.local.fileAdded.connect(self.onAdded)
            self.local.fileChanged.connect(self.onChanged)
            self.local.fileDeleted.connect(self.onDeleted)

            self.deleteServerFile.connect(self.server.onDelete)
            self.downloadFile.connect(self.server.onDownload)
            self.uploadFile.connect(self.server.onUpload)

    @Slot()
    def initQueue(self):
        self.actionQueue = ActionQueue()
        
        self.actionTimer = QTimer()
        self.actionTimer.setInterval(5000)
        self.actionTimer.timeout.connect(self.takeAction)
        
        self.actionTimer.start()
    
    @Slot()
    def takeAction(self):
        self.actionTimer.stop()

        if self.doPreemptive:
            # Preemptive check is a bit of a workaround to deal with
            # initial unexpected conditions: database file is gone
            self.doPreemptive = False
            self.server.preemptiveCheck = True
            self.local.fileAdded.connect(self.server.added)
            self.local.checkout()
            self.server.checkout()
            self.local.fileAdded.disconnect(self.server.added)
            self.server.preemptiveCheck = False
            for action in self.server.preemptiveActions:
                self.actionQueue.add(action)
        
        # After preemptive check, it is safe to do the connections
        # for normal operations
        self.connections()

        for action in self.actionQueue:
            if action is not None:
                print 'Next action: %s' % action 
                path = action.path
                do = action.action
                location = action.location
                
                if do == FileAction.UPLOAD:
                    self.uploadFile.emit(path)
                elif do == FileAction.DOWNLOAD:
                    self.downloadFile.emit(path)
                elif do == FileAction.DELETE:
                    with File.fromPath(path) as deleted_file:
                        # `action.location` attribute only makes sense when deciding
                        # whether to delete a file on the server or local.
                        if location == FileAction.LOCAL:
                            localpath = self.local.localFromServer(path)
                            
                            try:
                                os.remove(localpath)
                            except:
                                pass
                            
                            deleted_file.inlocal = False
                        elif location == FileAction.SERVER:
                            self.deleteServerFile.emit(path)
                            deleted_file.inserver = False
        
        self.actionQueue.clear()
        self.server.checkout()
        if self.firstScan:
            # First do a full scan to check for offline changes.
            # From there we will rely on real time notifications watchdog.
            self.firstScan = False
            self.local.checkout()
            self.local.startObserver()
        self.cleanSync()
        self.actionTimer.start()
            
    @Slot()
    def cleanSync(self):
        """
        Removes entries from the database for deleted files
        """
        
        session = Session()
        session.query(File).filter(File.inserver == False).filter(File.inlocal == False).delete()
        session.commit()

    @Slot(str, str)
    def onChanged(self, location, serverpath):
        changed_file = File.fromPath(serverpath)
        action = None
        
        if not changed_file.servermdate:
            # Probably a local added event that also
            # spawned a modified event.
            return

        print 'Changed here %s, there %s delta %s' % (
                    changed_file.localmdate, changed_file.servermdate,
                    (changed_file.localmdate - changed_file.servermdate).total_seconds())
        
        try:
            diff = changed_file.timeDiff()
            
            if abs(diff) < 5:
                return
            
            if location == FileAction.SERVER:
                if changed_file.inlocal:
                    if changed_file.localmdate < changed_file.servermdate:
                        action = FileAction(serverpath, FileAction.DOWNLOAD, FileAction.LOCAL)
                else:
                    action = FileAction(serverpath, FileAction.DOWNLOAD, FileAction.LOCAL)
           
            elif location == FileAction.LOCAL:
                if changed_file.inserver:
                    try:
                        if changed_file.servermdate < changed_file.localmdate:
                            action = FileAction(serverpath, FileAction.UPLOAD, FileAction.SERVER)
                    except:
                        print 'Error:', changed_file, changed_file.servermdate, changed_file.localmdate
                        
                else:
                    action = FileAction(serverpath, FileAction.UPLOAD, FileAction.SERVER)
                
            if action is not None:
                self.actionQueue.add(action)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            
    
    @Slot(str, str)
    def onAdded(self, location, serverpath):
        added_file = File.fromPath(serverpath)
        action = None
        
        if location == FileAction.SERVER and not added_file.inlocal:
            action = FileAction(serverpath, FileAction.DOWNLOAD, FileAction.LOCAL)
        elif location == FileAction.LOCAL and not added_file.inserver:
            action = FileAction(serverpath, FileAction.UPLOAD, FileAction.SERVER)
            
        if action is not None:
            self.actionQueue.add(action)
        
    @Slot(str, str)
    def onDeleted(self, location, serverpath):
        deleted_file = File.fromPath(serverpath)
        action = None
        
        if location == FileAction.SERVER:
            if deleted_file.inlocal:
                action = FileAction(serverpath, FileAction.DELETE, FileAction.LOCAL)
        elif location == FileAction.LOCAL:
            if deleted_file.inserver:
                action = FileAction(serverpath, FileAction.DELETE, FileAction.SERVER)
        
        if action is not None:
            self.actionQueue.add(action)
            
    
