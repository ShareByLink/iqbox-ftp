import os
import sys
import time
import traceback
from datetime import datetime as dt
from datetime import timedelta as td
from ftplib import FTP_TLS, FTP, error_reply, error_perm

from PySide.QtCore import QObject, Signal, Slot, QTimer, QDir, QThread

from dbcore import File, FileAction, Session
from localsettings import DEBUG


def pause_timer(f):
    def wrapped(self):
        if DEBUG:
            #print 'Started {0}'.format(self.LOCATION)
            pass
        try:
            self.checkTimer.stop()
        except AttributeError:
            pass
        f(self)
        try:
            self.checked.emit()
            self.checkTimer.start()
        except AttributeError:
            pass
        if DEBUG:
            #print 'Ended {0}'.format(self.LOCATION)
            pass
        
    return wrapped
        

class Watcher(QObject):

    fileDeleted = Signal((str,str,))
    fileAdded = Signal((str,str,))
    fileChanged = Signal((str,str,))
    checked = Signal()
    
    TOLERANCE = 5
    
    def __init__(self, parent=None):
        super(Watcher, self).__init__(parent)
        
    @Slot()
    def checkout(self):
        raise NotImplementedError
    
    @Slot()
    def startCheckout(self):
        self.checkTimer = QTimer()
        self.checkTimer.setInterval(self.interval)
        self.checkTimer.timeout.connect(self.checkout)
        
        self.checkTimer.start()
        
    @Slot(str, str)
    def added(self, location, serverpath):
        print 'Added {0}: {1}'.format(self.LOCATION, serverpath)
        
    @Slot(str, str)
    def changed(self, location, serverpath):
        print 'Changed {0}: {1}'.format(self.LOCATION, serverpath)
        
    @Slot(str, str)
    def deleted(self, location, serverpath):
        print 'Deleted {0}: {1}'.format(self.LOCATION, serverpath)

    def localFromServer(self, serverpath):
        # Removing leading '/' so `os.path.join` doesn't treat
        # `localpath` as an absolute path
        localpath = serverpath[1:] if serverpath.startswith('/') else serverpath
        localpath = QDir.toNativeSeparators(localpath)
        localpath = os.path.join(self.localdir, localpath)
        
        return localpath
        
    def serverFromLocal(self, localpath):
        serverpath = localpath.replace(self.localdir, '')
        serverpath = QDir.fromNativeSeparators(serverpath)
        
        return serverpath

class ServerWatcher(Watcher):

    downloadProgress = Signal((int, int,))
    uploadProgress = Signal((int, int,))
    fileEvent = Signal((str,))
    fileEventComplete = Signal()    
    
    LOCATION = 'server'
    
    def __init__(self, host, ssl, parent=None):
        """
        Initializes parent class and attributes. Decides
        whether to use `FTP_TLS` or `FTP` based on the `ssl` param.
        
        :param host: Location of the FTP server
        :param ssl: Tells whether the FTP needs to support TLS or not
        :param parent: Reference to a `QObject` instance a parent
        """
        
        super(ServerWatcher, self).__init__(parent)
        
        self.interval = 5000
        self.localdir = ''
        self.deleteQueue = []
        self.downloadQueue = []
        self.uploadQueue = []
        self.ftp = FTP_TLS(host) if ssl is True else FTP(host)
        
        self.preemptiveCheck = False
        self.preemptiveActions = []

    @property
    def currentdir(self):
        """Returns the current working directory at the server"""
        
        return self.ftp.pwd()
        
    def setLocalDir(self, localdir):
        """
        Sets the local directory used to stored all
        downloaded files. Creates the directory if needed.
        
        :param localdir: Absolute path to local directory
        """
        
        self.localdir = localdir
        if not os.path.exists(self.localdir):
            os.makedirs(self.localdir)
    
    @pause_timer
    @Slot()
    def checkout(self):
        """
        Recursively checks out all files on the server.
        Returns a dictionary of files on the server with their last modified date.
        
        :param download: Indicates whether or not the files should be downloaded
        """
        
        # Check  `self.deleteQueue`, `self.uploadQueue` and `self.downloadQueue` queues.
        # These tasks are done in queues to make sure all FTP commands
        # are done sequentially, in the same thread.
        self.deleteAll()
        self.uploadAll()
        self.downloadAll()
        
        # Handy list to keep track of the checkout process.
        # This list contain absolute paths only.
        checked_dirs = list()

        # Sets '/' as initial directory and initializes `downloading_dir`
        self.ftp.cwd('/')
        downloading_dir = self.currentdir
        check_date = dt.utcnow()

        while True:
            # Gets the list of sub directories and files inside the 
            # current directory `downloading_dir`.
            dir_subdirs = self.getDirs(downloading_dir)
            dirfiles = self.getFiles(downloading_dir)
           
            # Leading '/' in `downloading_dir` breaks the `os.path.join` call
            localdir = os.path.join(self.localdir, downloading_dir[1:])
            if not os.path.exists(localdir):
                # Creates the directory if it doesn't already exists.
                os.makedirs(localdir)

            for file_ in dirfiles:
                # `serverpath` is the absolute path of the file on the server,
                # download it only if it hasn't been already downloaded
                serverpath = os.path.join(downloading_dir, file_)
                serverpath = QDir.fromNativeSeparators(serverpath)
                server_file = File.fromPath(serverpath)
                if server_file.last_checked_server != check_date:
                    # Do this process only once per file        
                    just_added = not server_file.inserver
                    lastmdate = server_file.servermdate
                    servermdate = self.lastModified(serverpath)
                    
                    server_file.inserver = True
                    server_file.last_checked_server = check_date
                    server_file.servermdate = servermdate
                    server_file.session.commit()
                    
                    delta = 0
                    if server_file.inlocal:
                        delta = server_file.timeDiff()

                    # Emit the signals after the attributes has been set and committed
                    if just_added is True:
                        self.fileAdded.emit(ServerWatcher.LOCATION, serverpath)
                    elif server_file.servermdate > lastmdate or delta < -Watcher.TOLERANCE:
                        self.fileChanged.emit(ServerWatcher.LOCATION, serverpath) 
            
            dir_ready = True
            for dir_ in dir_subdirs:
                # `dirpath` is the absolute path of the subdirectory on the server,
                dirpath = os.path.join(downloading_dir, dir_)
                # `downloading_dir` is ready only when all its subdirectory are on the 
                # `checked_dirs` list.
                if dirpath not in checked_dirs:
                    # Found one subdirectory that is not on `checked_dirs`,
                    # will process it in the next iteration.
                    downloading_dir = dirpath
                    dir_ready = False
                    break
                    
            if dir_ready is True:
                # All subdirectories of `downloading_dir` are already in `checked_dirs`
                if downloading_dir == '/':
                    # All directories ready and at '/', means checkout is complete
                    break
                    
                else:
                    # Not at '/'. Current directory is ready so is appended to `checked_dirs`
                    # Back one directory to find directories that are not in `checked_dirs`
                    checked_dirs.append(downloading_dir)
                    downloading_dir = os.path.dirname(downloading_dir)
                    
        # Deleted files are the ones whose `last_checked_server` attribute 
        # didn't get updated in the recursive run.
        session = Session()
        deleted = session.query(File).filter(File.last_checked_server < check_date).filter(File.inserver == True)
        for file_ in deleted:
            self.fileDeleted.emit(ServerWatcher.LOCATION, file_.path)
        
        # Wraps up the checkout process, commits to the database.
        session.commit()
                
    def getFiles(self, path):
        """
        This method simply wraps the `nlst` method with an exception handler,
        and returns an empty list in case an exception is caught.
        
        :param path: Relative or absolute path on the server
        """
        
        try:
            nlst = self.ftp.nlst(path)
            dirs = self.getDirs(path)
            
            # Files are items in nlst that are not in dirs
            files = [item for item in nlst if os.path.basename(item) not in dirs]
            
            return files
        except:
            print 'Exception in ServerWatcher.getDirs'
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            return []
             
    def getDirs(self, path):
        """
        Retrieves a list of the directories inside `path`,
        uses `retrlines` and the LIST command to retrieve the items.
        
        :param path: Relative or absolute path on the server
        """
        
        dirs = list()
        def handleLine(line):
            """
            Recieves a line from the LIST command.
            This function is meant to be used as callback for the `retrlines` method.
            
            :params line: Line from the LIST command
            """

            if line.startswith('d'):
                # Only lines starting with 'd' are directories
                # Parse the directory out of the line; lines look like:
                # 'drwxrwxrwx   1 user     group           0 Jun 15  2012 dirname'
                dirname = line[55:].strip()
                if dirname != '.' and dirname != '..':
                    # Ignoring '.' and '..' entries
                    dirs.append(dirname)
        
        try:
            self.ftp.retrlines('LIST %s' % path, handleLine)
            
            return dirs
        except:
            print 'Exception in ServerWatcher.getDirs'
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            return []
    
    @Slot(str)
    def onDelete(self, filename):
        self.deleteQueue.append(filename)
        
    def deleteNext(self):
        if len(self.deleteQueue) > 0:
            next = self.deleteQueue.pop(0)
            self.deleteFile(next)
    
    def deleteAll(self):
        for filename in self.deleteQueue:
            self.deleteFile(filename)
            
        self.deleteQueue = []
    
    @Slot(str)
    def deleteFile(self, filename):
        """
        Deletes the file `filename` to the server
        
        :param filename: Absolute or relative path to the file
        """
        
        try:
            print 'Deleting %s' % filename
            self.ftp.delete(filename)
            return True
        except (error_reply, error_perm):
            print 'Error deleting %s' % filename
            return False
        
    @Slot(str)
    def onDownload(self, filename):
        self.downloadQueue.append(filename)
        
    def downloadNext(self):
        if len(self.downloadQueue) > 0:
            next = self.downloadQueue.pop(0)
            self.downloadFile(next)
            
    def downloadAll(self):
        for filename in self.downloadQueue:
            self.downloadFile(filename)
            
        self.downloadQueue = []
    
    @Slot(str, str)   
    def downloadFile(self, filename, localpath=None):
        """
        Performs a binary download to the file `filename` located on the server.
        `filename` parameter can be either absolute or relative, though it can
        fail for relative paths if the current directory is not appropiate.
        
        :param filename: Relative or absolute path to the file
        :param localpath: Absolute local path where the file will be saved
        """
        
        def handleChunk(chunk):
            """
            Receives chuncks of data downloaded from the server.
            This function is meant to be used as callback for the `retrbinary` method.
            
            :params chunk: Chunk of downloaded bytes to be written into the file
            """
        
            # Simply writes the received data into the file `self.downloading`
            self.downloading.write(chunk)
            self.download_progress += len(chunk)
            self.downloadProgress.emit(self.download_size, self.download_progress)
        
        
        if localpath is None:
            localpath = self.localFromServer(filename)
        
        localdir = os.path.dirname(localpath)
        if not os.path.exists(localdir):
            # Creates the directory if it doesn't already exists.
            os.makedirs(localdir)
        
        with open(localpath, 'wb') as f:
            # Opens the file at `localname` which will hold the downloaded file.
            # Object attributes regarding download status are updated accordingly.
            print 'Downloading: %s to %s' % (filename, localpath)
            self.fileEvent.emit(filename)
            self.downloading = f
            self.download_progress = 0

            try:
                self.download_size = int(self.ftp.sendcmd('SIZE %s' % filename).split(' ')[-1])
                self.ftp.retrbinary('RETR %s' % filename, handleChunk)
                
                print 'Download finished'
                
                # Let's set the same modified time on the server to match
                # the one in local.          
                with File.fromPath(filename) as downloadedfile:
                    mdate = LocalWatcher.lastModified(localpath)
                    downloadedfile.localmdate = mdate
                    downloadedfile.servermdate = mdate
                    
                self.ftp.sendcmd('MDTM %s %s' % (mdate.strftime('%Y%m%d%H%M%S'), filename))

                downloaded = True
            except (error_reply, error_perm) as ftperr:
                print 'Error downloading %s, %s' % (filename, ftperr)
                downloaded = False
                
            self.fileEventComplete.emit()
            
            return downloaded
    
    @Slot(str)
    def onUpload(self, filename):
        self.uploadQueue.append(filename)
    
    def uploadNext(self):
        if len(self.uploadQueue) > 0:
            next = self.uploadQueue.pop(0)
            self.uploadFile(next)
            
    def uploadAll(self):
        for filename in self.uploadQueue:
            self.uploadFile(filename)
            
        self.uploadQueue = []
            
    @Slot(str)
    def uploadFile(self, filename):
        """
        Uploads the file `filename` to the server, creating
        the needed directories.
        
        :param filename: Absolute or relative path to the file
        """
        
        def handle(buf):
            """This function is meant to be used as callback for the `storbinary` method."""
        
            self.upload_progress += 1024
            self.uploadProgress.emit(self.upload_size, self.upload_progress)
        
        
        # Creates the directory where the file will be uploaded to
        self.mkpath(os.path.dirname(filename))
        
        localpath = self.localFromServer(filename)
        print 'Uploading %s to %s' % (localpath, filename)
        
        try:
            # Uploads file and updates its modified date in the server
            # to match the date in the local filesystem.
            self.upload_progress = 0
            self.upload_size = os.path.getsize(localpath)
            self.fileEvent.emit(localpath)
            self.ftp.storbinary('STOR %s' % filename,
                                open(localpath, 'rb'), 
                                1024,
                                handle)
            print 'Upload finished'
            with File.fromPath(filename) as uploaded:
                modified = uploaded.localmdate
                uploaded.servermdate = modified
                
                self.ftp.sendcmd('MDTM %s %s' % (modified.strftime('%Y%m%d%H%M%S'), filename))
            
            uploaded = True
        except (error_reply, error_perm, OSError) as err:
            print 'Error uploading %s, %s' % (filename, err)
            uploaded = False
            
        self.fileEventComplete.emit()
        
        return uploaded
            
    def lastModified(self, filename):
        """
        Uses the MDTM FTP command to find the last modified timestamp
        of the file `filename`.
        Returns a `datetime.datetime` object in UTC representing the file's
        last modified date and time.
        
        :param filename: Relative or absolute path to the file
        """
        
        timestamp = self.ftp.sendcmd('MDTM %s' % filename)
        timestamp = timestamp.split(' ')[-1]
        dateformat = '%Y%m%d%H%M%S.%f' if '.' in timestamp else '%Y%m%d%H%M%S'
        
        return dt.strptime(timestamp, dateformat)
    
    def mkpath(self, path):
        """
        Creates the path `path` on the server by recursively 
        created folders, if needed.
        
        :param path: Absolute path on the server to be created
        """
        
        try:
            self.ftp.cwd(path)
        except error_perm:
            # `cwd` call failed. Need to create some folders
            make_dir = '/' 
            steps = path.split('/')
            for step in steps:
                if len(step) == 0:
                    continue
                make_dir += '%s/' % step
                try:
                    self.ftp.mkd(make_dir)
                except error_perm:
                    # Probably already exists
                    continue
        else:
            # `cwd` call succeed. No need to create
            # any folders
            self.ftp.cwd('/')
            return
            
    @Slot(str, str)
    def added(self, location, serverpath):
        super(ServerWatcher, self).added(location, serverpath)
        
        def actionFromPath(serverpath):
            f = File()
            f.servermdate = self.lastModified(serverpath)
            f.localmdate = LocalWatcher.lastModified(self.localFromServer(serverpath))
            diff = f.timeDiff()
            action = None
            if abs(diff) > Watcher.TOLERANCE:
                if diff > 0:
                    action = FileAction(serverpath, FileAction.UPLOAD, ServerWatcher.LOCATION)
                else:
                    action = FileAction(serverpath, FileAction.DOWNLOAD, LocalWatcher.LOCATION)
            
            return action
            
        if self.preemptiveCheck:
            if location == ServerWatcher.LOCATION:
                localpath = self.localFromServer(serverpath)
                if not os.path.exists(localpath):
                    action = FileAction(serverpath, FileAction.DOWNLOAD, ServerWatcher.LOCATION)
                    self.preemptiveActions.append(action)
                else:
                    action = actionFromPath(serverpath)
                    if action is not None:
                        self.preemptiveActions.append(action) 

            elif location == LocalWatcher.LOCATION:
                try:
                    self.ftp.sendcmd('SIZE %s' % serverpath)
                except (error_reply, error_perm):
                    exists = False
                else:
                    exists = True
                if not exists:
                    action = FileAction(serverpath, FileAction.UPLOAD, LocalWatcher.LOCATION)
                    self.preemptiveActions.append(action)
                else:
                    action = actionFromPath(serverpath)
                    if action is not None:
                        self.preemptiveActions.append(action) 

    @Slot(str, str)
    def changed(self, location, serverpath):
        super(ServerWatcher, self).changed(location, serverpath)
            
    @Slot(str, str)
    def deleted(self, location, serverpath):
        super(ServerWatcher, self).deleted(location, serverpath)
        with File.fromPath(serverpath) as deleted:
            deleted.inserver = False
            
            
class LocalWatcher(Watcher):
    
    LOCATION = 'local'
    
    def __init__(self, localdir, parent=None):
        super(LocalWatcher, self).__init__(parent)
        
        self.localdir = localdir
        self.interval = 2000
    
    @pause_timer
    @Slot()
    def checkout(self):
        check_date = dt.utcnow()
        for item in os.walk(self.localdir):
            directory = item[0]
            subfiles = item[-1]

            for file_ in subfiles:
                localpath = os.path.join(directory, file_)
                localmdate = LocalWatcher.lastModified(localpath)
                serverpath = self.serverFromLocal(localpath)

                with File.fromPath(serverpath) as local_file:
                    just_added = not local_file.inlocal
                    lastmdate = local_file.localmdate
                         
                    local_file.inlocal = True
                    local_file.last_checked_local = check_date
                    local_file.localmdate = localmdate
                    
                    delta = 0
                    if local_file.inserver:
                        delta = local_file.timeDiff()
                    
                # Emit the signals after the attributes has been set
                # and committed.
                if just_added is True:
                    self.fileAdded.emit(LocalWatcher.LOCATION, serverpath)
                elif localmdate > lastmdate or delta > Watcher.TOLERANCE:
                    self.fileChanged.emit(LocalWatcher.LOCATION, serverpath)

        # Deleted files are the ones whose `last_checked_local` attribute 
        # didn't get updated in the recursive run.
        session = Session()
        deleted = session.query(File).filter(File.last_checked_local < check_date).filter(File.inlocal == True)
        for file_ in deleted:
            self.fileDeleted.emit(LocalWatcher.LOCATION, file_.path)
            
        session.commit()
        
    @classmethod
    def lastModified(cls, localpath):
        return dt.utcfromtimestamp(os.path.getmtime(localpath))
        
    @Slot(str, str)
    def deleted(self, location, serverpath):
        super(LocalWatcher, self).deleted(location, serverpath)
        with File.fromPath(serverpath) as deleted:
            deleted.inlocal = False
        

if __name__ == '__main__':
    
    localApp = LocalWatcher('C:\\Windows\\win32')
    localpath = localApp.localFromServer('/home/text.cc')
    serverpath = localApp.serverFromLocal(localpath)
    
    print serverpath, localpath
    
    app3 = ServerWatcher('ops.osop.com.pa', False)
    app3.setLocalDir('/home/sergio/Documents/FTPSync/mareas')
    print app3.ftp.login('mareas', 'mareas123')
    time = app3.lastModified('/test.txt')
    print 'Mareas UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    cmd = 'MDTM %s %s' % (dt.utcnow().strftime('%Y%m%d%H%M%S'), '/test.txt')
    print cmd
    print app3.ftp.sendcmd(cmd)
    time = app3.lastModified('/test.txt')
    print 'UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    
    print 'Dirs in "/": %s' % app3.getDirs('/')
    print 'Files in "/": %s' % app3.getFiles('/')
    
    app3.checkout()
    
    app3.mkpath('/folder/other/one/two/three/')
    app3.mkpath('/folder/other/one/two/three/four')
    app3.mkpath('/folder/other/one/two/three/four')
    raise SystemExit("Exit here please")
    
    app2 = ServerWatcher('10.18.210.193', False)
    app2.setLocalDir('/home/sergio/Documents/FTPSync/book')
    print app2.ftp.login('sergio', 'lopikljh')
    
    time = app2.lastModified('/Public/Files/Qt/time.txt')
    print 'Book UTC: %s, Local: %s' % (time, time - timedelta(hours=5))
    
    cmd = 'MDTM %s %s' % (dt.utcnow().strftime('%Y%m%d%H%M%S'), '/Public/Files/Qt/time.txt')
    print cmd
    app2.ftp.sendcmd(cmd)
    time = app2.lastModified('/Public/Files/Qt/time.txt')
    print 'UTC: %s, Local: %s' % (time, time - timedelta(hours=5))
    
    print 'Dirs in "/": %s' % app2.getDirs('/')
    print 'Files in "/": %s' % app2.getFiles('/')

    app1 = ServerWatcher('ftp7.iqstorage.com', True)
    app1.ftp.login('serpulga', 'iqstorage')
    app1.setLocalDir('/home/sergio/Documents/FTPSync/iq')
    time = app1.lastModified('/4.89 MB Download.bin')
    
    print 'Dirs in "/": %s' % app1.getDirs('/')
    print 'Files in "/": %s' % app1.getFiles('/')
    
    print 'IQ UTC: %s, Local: %s' % (time, time - timedelta(hours=5))
    
    cmd = 'MDTM %s %s' % (dt.utcnow().strftime('%Y%m%d%H%M%S'), '/4.89 MB Download.bin')
    print cmd
    app1.ftp.sendcmd(cmd)
    time = app1.lastModified('/4.89 MB Download.bin')
    print 'UTC: %s, Local: %s' % (time, time - timedelta(hours=5))
    
    