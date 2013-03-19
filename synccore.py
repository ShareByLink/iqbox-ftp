import os
import sys
import traceback

from PySide.QtCore import QObject, Slot, Signal, QTimer, QDir, QThread

from filebase import File, FileAction, ActionQueue, Session


class SyncCore(QObject):
    
    deleteServerFile = Signal((str,))
    downloadFile = Signal((str,))
    uploadFile = Signal((str,))
    
    def __init__(self, localdir, parent=None):
        super(SyncCore, self).__init__(parent)
        
        self.localdir = localdir
        self.localAdds = []
        self.serverAdds = []
        
    @Slot()
    def initQueue(self):
        self.action_queue = ActionQueue()
        self.action_queue.clear()
        
        self.actionTimer = QTimer()
        self.actionTimer.setInterval(5000)
        self.actionTimer.timeout.connect(self.takeAction)
        
        self.actionTimer.start()
    
    @Slot()
    def takeAction(self):
        action = self.action_queue.next()
        
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
                        localpath = path[1:] if path.startswith('/') else path
                        localpath = QDir.toNativeSeparators(localpath)
                        localpath = os.path.join(self.localdir, localpath)
                        
                        try:
                            os.remove(localpath)
                        except:
                            pass
                        
                        deleted_file.inlocal = False
                    elif location == FileAction.SERVER:
                        self.deleteServerFile.emit(path)
                        deleted_file.inserver = False

            self.action_queue.remove(action)
            
        if len(self.action_queue) == 0:
            session = Session()
            session.query(File).filter(File.inserver == False).filter(File.inlocal == False).delete()
            session.commit()
            
    @Slot()
    def onFtpDone(self):
        """
        Slot. Should be triggered when the FTP commads are all done,
        this method checks if the sync is complete        
        """
        
        # This method will be used as a sync fallback.
        # In case `self.action_queue`, the database will be
        # queries looking for unsynced files. 
        if len(self.action_queue) == 0:
            session = Session()
            
            for file_ in session.query(File).filter(File.inserver != File.inlocal):
                # Unsynced: In one place but not the other.
                if file_.inserver:
                    location = FileAction.SERVER
                else:
                    location = FileAction.LOCAL
                self.onAdded(FileAction.LOCAL, file_.path)
        
    @Slot(str, str)
    def onChanged(self, location, serverpath):
        changed_file = File.fromPath(serverpath)
        action = None
        
        print 'Changed here %s, there %s delta %s' % (
                    changed_file.localmdate, changed_file.servermdate,
                    (changed_file.localmdate - changed_file.servermdate).total_seconds())
        
        try:
            diff = (changed_file.localmdate - changed_file.servermdate).total_seconds()
            
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
                self.action_queue.add(action)
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
            self.action_queue.add(action)
        
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
            self.action_queue.add(action)
            
    