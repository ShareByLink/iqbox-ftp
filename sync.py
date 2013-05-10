import os
import sys
import traceback

import engine_tools

from filetransfer_abc import ftp_si

from PySide.QtCore import QObject, Slot, Signal, QTimer, QDir, QThread

from dbcore import File, FileAction, ActionQueue, Session, empty_db
from watchers import ServerWatcher, LocalWatcher


class Sync(QObject):
    
    deleteServerFile = Signal((str,))
    deleteLocalFile = Signal((str,))
    downloadFile = Signal((str,))
    uploadFile = Signal((str,))
    checkServer = Signal()
    checkLocal = Signal()
    statusChanged = Signal((str,))

    def __init__(self, host, ssl, parent=None):
        super(Sync, self).__init__(parent)

        self.server = ServerWatcher(host, ssl, self)
        
        self.preloaedActions = []
        self.doPreemptive = empty_db()
        self.connected = False
        self.firstScan = True
        
    def setLocalDir(self, localdir):
        if not os.path.exists(localdir):
            # Creates the directory if it doesn't already exists.
            os.makedirs(localdir)
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

            self.deleteLocalFile.connect(self.local.deleteFile)
            self.deleteServerFile.connect(self.server.onDelete)
            self.downloadFile.connect(self.server.onDownload)
            self.uploadFile.connect(self.server.onUpload)

    @Slot()
    def initQueue(self):
        self.actionQueue = ActionQueue()
        
        self.actionTimer = QTimer()
        self.actionTimer.setInterval(1)
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

        serverActionCount = 0
        localActionCount = 0
        for action in self.actionQueue:
            if action is not None:
                print 'Next action: %s' % action 
                path = action.path
                do = action.action
                location = action.location
                
                if location == FileAction.LOCAL and (do == FileAction.UPLOAD \
                   or do == FileAction.DELETE):
                    if not engine_tools.file_exists_local(path):
                        # File no longer exists at the time of processing.
                        # Maybe it was temporary or a quick rename.
                        # So we ignore it
                        print "Ignored action on " + path + ": File doesn't exist on local."
                        continue
                    
                
                if do == FileAction.UPLOAD:
                    self.uploadFile.emit(path)
                    localActionCount += 1
                elif do == FileAction.DOWNLOAD:
                    self.downloadFile.emit(path)
                    serverActionCount += 1
                elif do == FileAction.DELETE:
                    with File.fromPath(path) as deleted_file:
                        # `action.location` attribute only makes sense when deciding
                        # whether to delete a file on the server or local.
                        if location == FileAction.LOCAL:
                            localpath = self.local.localFromServer(path)
                            self.deleteLocalFile.emit(localpath)
                            deleted_file.inlocal = False
                            localActionCount += 1

                        elif location == FileAction.SERVER:
                            self.deleteServerFile.emit(path)
                            deleted_file.inserver = False
                            serverActionCount += 1
        
        self.actionQueue.clear()
        
        # Scan server for file changes
        self.statusChanged.emit('Scanning remote files for changes')
        self.server.checkout()
        
        if self.firstScan:
            # First do a full scan to check for offline changes.
            # From there we will rely on real time notifications watchdog.
            self.firstScan = False
            self.statusChanged.emit('Scanning local files for changes')
            self.local.checkout()
            self.local.startObserver()
            # Si Added
            # Since its the first scan, we should also
            # set the timer interval
            self.actionTimer.setInterval(5000)        
        self.cleanSync()

        # Si Added
        # Set check interval intelligently.
        # If there's no activity there, wait longer.
        # Since if there's just no usage, then
        # no reason to take up CPU cycles.
        tempInterval = 0
        if serverActionCount+localActionCount > 0:
            tempInterval = 5000
        else:
            tempInterval = 1000 * 10
        
        self.actionTimer.start()
            
    @Slot()
    def cleanSync(self):
        """
        Removes entries from the database for deleted files
        """
        
        session = Session()
        session.query(File).filter(File.inserver == False).filter(File.inlocal == False).delete(synchronize_session=False)
        session.commit()
        self.statusChanged.emit('Sync completed. Waiting for changes')

    @Slot(str, str, bool)
    def onChanged(self, location, serverpath, skipDeltaCheck):
        changed_file = File.fromPath(serverpath)
        action = None
        
        #if not changed_file.servermdate:
            # Probably a local added event that also
            # spawned a modified event.
            #return

        file_name_only = os.path.basename(serverpath)
        if engine_tools.isTemporaryFile(file_name_only):
            print 'File ' + serverpath + ' ignored since it is a temporary file'
            return
           
        print 'File ' + serverpath + ':'
        
        if changed_file.servermdate == None:
            mydiff = "** File Not in Server **"
            edit_time = "(not in server)"
        else:
            ttt = (changed_file.localmdate - changed_file.servermdate).total_seconds() 
            mydiff = str( ttt )
            edit_time = str(changed_file.servermdate)
        
        print 'Changed here %s, there %s delta %s' % (
                    changed_file.localmdate, edit_time, mydiff)
                    
        
        try:
            if changed_file.inserver:
                diff = changed_file.timeDiff()

                MY_TOLERANCE = 10
            
                if skipDeltaCheck == False and abs(diff) < MY_TOLERANCE:
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

        file_name_only = os.path.basename(serverpath)
        if engine_tools.isTemporaryFile(file_name_only):
            print 'File ' + serverpath + ' was created but ignored since it is a temporary file'
            return
        
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

        # NOTE: For temporary files, the current action is to delete it.
        # Reason 1: We need to remove it from the database.
        # Reason 2: If somehow there is a temporary file 
        # there on the other side, then it makes sense to delete it.
        
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
            
    
