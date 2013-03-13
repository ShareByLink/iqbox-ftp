import os
import sys
import traceback
from datetime import datetime as dt
from ftplib import FTP_TLS, FTP, error_reply, error_perm

from PySide.QtCore import QObject, Signal, Slot, QTimer, QDir
from filebase import File, Session

 
class FtpObject(QObject):
    
    downloadProgress = Signal((int, int,))
    uploadProgress = Signal((int, int,))
    fileEvent = Signal((str,))
    fileEventComplete = Signal()
    checkoutDone = Signal()
    checkedFile = Signal((str, dt,))
    fileDeleted = Signal((str,str,))
    fileAdded = Signal((str,str,))
    fileChanged = Signal((str,str,))
    
    LOCATION = 'server'
    
    def __init__(self, host, ssl, parent=None):
        """
        Initializes parent class and attributes. Decides
        whether to use `FTP_TLS` or `FTP` based on the `ssl` param.
        
        :param host: Location of the FTP server
        :param ssl: Tells whether the FTP needs to support TLS or not
        :param parent: Reference to a `QObject` instance a parent
        """
        
        super(FtpObject, self).__init__(parent)
        
        self.localdir = ''
        self.ftp = FTP_TLS(host) if ssl is True else FTP(host)

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
    
    @Slot(bool)
    def checkout(self, download=False):
        """
        Recursively checks out all files on the server.
        Returns a dictionary of files on the server with their last modified date.
        
        :param download: Indicates whether or not the files should be downloaded
        """
        
        # Handy list to keep track of the checkout process.
        # This lists contain absolute paths only.
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
                with File.fromPath(serverpath) as server_file:
                    if server_file.last_checked_server != check_date:
                        # Do this process only once per file
                        if download is True:
                            self.downloadFile(serverpath)
                            
                        just_added = not server_file.inserver
                        lastmdate = server_file.servermdate
                        
                        server_file.inserver = True
                        server_file.last_checked_server = check_date
                        server_file.servermdate = self.lastModified(serverpath)
                        
                        server_file.session.commit()
                        # Emit the signals after the attributes has been set and committed
                        if just_added is True:
                            self.fileAdded.emit(FtpObject.LOCATION, serverpath)
                        elif server_file.servermdate > lastmdate:
                            self.fileChanged.emit(FtpObject.LOCATION, serverpath)
    
                        self.checkedFile.emit(server_file.path, server_file.servermdate)
            
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
            self.fileDeleted.emit(FtpObject.LOCATION, file_.path)
        
        session.commit()
        QTimer.singleShot(5000, self.checkout)
        self.checkoutDone.emit()
                
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
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
             
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
        
        self.ftp.retrlines('LIST %s' % path, handleLine)
        return dirs
    
    @Slot(str)
    def deleteFile(self, filename):
        """
        Deletes the file `filename` to the server
        
        :param filename: Absolute or relative path to the file
        """
        
        try:
            self.ftp.delete(filename)
            return True
        except error_reply:
            print 'Error deleting %s' % filename
            return False
         
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
            # Gets the absolute local file path corresponding to the file `filename`
            # removing '/' at the beginnig of `filename` so the `os.path.join` call works
            localpath = filename[1:] if filename.startswith('/') else filename
            localpath = QDir.toNativeSeparators(localpath)
            localpath = os.path.join(self.localdir, localpath)
        
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
            self.download_size = int(self.ftp.sendcmd('SIZE %s' % filename).split(' ')[-1])
            self.download_progress = 0

            try:
                self.ftp.retrbinary('RETR %s' % filename, handleChunk)
                
                # Let's set the same modified time in local: first find out the local difference
                # to utc, so `mdate` is the modified time in the server but on local time,
                # `int(mdate.total_seconds())`  to loose the milliseconds, the downloaded file
                # won't be uploaded because its local modified time will be older 
                # or equal to that on the server. 
                with File.fromPath(filename) as downloadedfile:
                    utcdiff = dt.now() - dt.utcnow() 
                    unixmdate = (downloadedfile.servermdate - dt(1970, 1, 1, 0, 0, 0)) + utcdiff
                    unixmdatestamp = int(unixmdate.total_seconds()) - 5
                    os.utime(localpath, (unixmdatestamp, unixmdatestamp))
                    downloadedfile.localmdate = downloadedfile.servermdate
                    
                downloaded = True
            except error_reply:
                print 'Error downloading %s' % filename
                downloaded = False
                
            self.fileEventComplete.emit()
            
            return downloaded
            
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
        
        # Removes leading separator
        localpath = filename[1:] if filename.startswith('/') else filename
        localpath = QDir.toNativeSeparators(localpath)
        localpath = os.path.join(self.localdir, localpath)
        
        # Creates the directory where the file will be uploaded to
        self.mkpath(os.path.dirname(filename))
        
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
            
            with File.fromPath(filename) as uploaded:
                modified = uploaded.localmdate
                uploaded.servermdate = modified
                self.ftp.sendcmd('MDTM %s %s' % (modified.strftime('%Y%m%d%H%M%S'), filename))
            
            uploaded = True
        except error_reply:
            print 'Error uploading %s' % filename
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
        print 'Added Server:', serverpath
        
    @Slot(str, str)
    def changed(self, location, serverpath):
        print 'Changed Server:', serverpath
        
    @Slot(str, str)
    def deleted(self, location, serverpath):
        with File.fromPath(serverpath) as deleted:
            deleted.inserver = False
            print 'Deleted Server:', serverpath
        
    
if __name__ == '__main__':
    app3 = FtpObject('ops.osop.com.pa', False)
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
    
    app3.checkout(False)
    
    app3.mkpath('/folder/other/one/two/three/')
    app3.mkpath('/folder/other/one/two/three/four')
    app3.mkpath('/folder/other/one/two/three/four')
    raise SystemExit("Exit here please")
    
    app2 = FtpObject('10.18.210.193', False)
    app2.setLocalDir('/home/sergio/Documents/FTPSync/book')
    print app2.ftp.login('sergio', 'lopikljh')
    
    time = app2.lastModified('/Public/Files/Qt/time.txt')
    print 'Book UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    
    cmd = 'MDTM %s %s' % (dt.utcnow().strftime('%Y%m%d%H%M%S'), '/Public/Files/Qt/time.txt')
    print cmd
    app2.ftp.sendcmd(cmd)
    time = app2.lastModified('/Public/Files/Qt/time.txt')
    print 'UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    
    print 'Dirs in "/": %s' % app2.getDirs('/')
    print 'Files in "/": %s' % app2.getFiles('/')

    app1 = FtpObject('ftp7.iqstorage.com', True)
    app1.ftp.login('serpulga', 'iqstorage')
    app1.setLocalDir('/home/sergio/Documents/FTPSync/iq')
    time = app1.lastModified('/4.89 MB Download.bin')
    
    print 'Dirs in "/": %s' % app1.getDirs('/')
    print 'Files in "/": %s' % app1.getFiles('/')
    
    print 'IQ UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    
    cmd = 'MDTM %s %s' % (dt.utcnow().strftime('%Y%m%d%H%M%S'), '/4.89 MB Download.bin')
    print cmd
    app1.ftp.sendcmd(cmd)
    time = app1.lastModified('/4.89 MB Download.bin')
    print 'UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    
    