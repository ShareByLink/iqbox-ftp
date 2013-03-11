import os
import sys
import traceback

from filebase import File, FileAction, ActionQueue, Session
from PySide.QtCore import QObject, Slot, Signal, QTimer, QDir


class SyncCore(QObject):
    
    deleteServerFile = Signal((str,))
    downloadFile = Signal((str,))
    uploadFile = Signal((str,))
    
    def __init__(self, localdir, parent=None):
        super(SyncCore, self).__init__(parent)
        
        self.localdir = localdir
        self.action_queue = ActionQueue()
        QTimer.singleShot(0, self.takeAction)
    
    @Slot()
    def takeAction(self):
        action = self.action_queue.next()
        
        if action is not None:
            print 'Action: %s' % action 
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
            
            wait_time = 5000            
        else:
            wait_time = 0
            
        QTimer.singleShot(wait_time, self.takeAction)
        
    @Slot(str, str)
    def onChanged(self, location, serverpath):
        changed_file = File.fromPath(serverpath)
        action = None
        
        try:
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
            
    