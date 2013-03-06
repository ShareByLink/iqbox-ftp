import os
import sys
import traceback

from filebase import File, FileAction, ActionQueue
from PySide.QtCore import QObject, Slot, Signal, QTimer


class SyncCore(QObject):
    
    deleteFile = Signal((str, str))
    downloadFile = Signal((str,))
    uploadFile = Signal((str,))
    
    def __init__(self, localdir, parent=None):
        super(SyncCore, self).__init__(parent)
        
        self.localdir = localdir
        self.action_queue = ActionQueue()
        self.action_timer = QTimer()
        
        self.action_timer.timeout.connect(self.takeAction)
        self.action_timer.setInterval(5000)
        self.action_timer.start()
        
    @Slot()
    def takeAction(self):
        print 'Actions: %s' % self.action_queue
        action = self.action_queue.next()
        
        if action.location == FileAction.LOCAL:
            os.path.join(self.localdir, action.path)

        if action is not None:
            self.action_queue.remove(action)
        
    @Slot()
    def onChanged(self, location, serverpath):
        changed_file = File.getFile(serverpath)
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
                    if changed_file.servermdate < changed_file.localmdate:
                        action = FileAction(serverpath, FileAction.UPLOAD, FileAction.SERVER)
                        
                else:
                    action = FileAction(serverpath, FileAction.UPLOAD, FileAction.SERVER)
                
            if action is not None:
                self.action_queue.add(action)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            
    
    @Slot()
    def onAdded(self, location, serverpath):
        self.onChanged(location, serverpath)
        
    @Slot()
    def onDeleted(self, location, serverpath):
        deleted_file = File.getFile(serverpath)
        action = None
        
        if location == FileAction.SERVER:
            if deleted_file.inlocal:
                action = FileAction(serverpath, FileAction.DELETE, FileAction.LOCAL)
        elif location == FileAction.LOCAL:
            if deleted_file.inserver:
                action = FileAction(serverpath, FileAction.DELETE, FileAction.SERVER)
        
        if action is not None:
            self.action_queue.add(action)
            
    