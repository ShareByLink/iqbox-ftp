import os
import sys
import traceback

from PySide.QtCore import QObject, Slot, Signal, QTimer, QDir, QThread

from dbcore import File, FileAction, ActionQueue, Session


class Sync(QObject):
    
    deleteServerFile = Signal((str,))
    downloadFile = Signal((str,))
    uploadFile = Signal((str,))
    checkServer = Signal()
    checkLocal = Signal()
    
    def __init__(self, localdir, actions=[], parent=None):
        super(Sync, self).__init__(parent)
        
        self.localdir = localdir
        self.preloaedActions = actions
        
    @Slot()
    def initQueue(self):
        self.actionQueue = ActionQueue(self.preloaedActions)
        
        self.actionTimer = QTimer()
        self.actionTimer.setInterval(5000)
        self.actionTimer.timeout.connect(self.takeAction)
        
        self.actionTimer.start()
    
    @Slot()
    def takeAction(self):
        self.actionTimer.stop()
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
                        
        self.actionQueue.clear()
        self.checkServer.emit()
        self.checkLocal.emit()
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
            
    