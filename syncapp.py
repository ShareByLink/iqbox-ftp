import os
import sys
import ftplib
import datetime
import threading
import time

from PySide.QtCore import QObject, Signal, Slot, QThread, QCoreApplication


dt = datetime.datetime
 

class FtpObject(QObject):
    
    downloadProgress = Signal((int, int,))
    downloadingFile = Signal((str,))
    checkoutDone = Signal((dict,))
 
    def __init__(self, host, ssl, parent=None):
        super(FtpObject, self).__init__(parent)
    
        self.localdir = ''
        
        def ftp():
            """
            This function creates an returns a `FtpApp` type object, which
            inherites from  either `ftplib.FTP_TLS` or `ftplib.FTP` given the `ssl` parameter.
            
            :param ssl: Select whether the FTP object needs TLS support or not
            :param args: Arguments that will be passed to the `SyncApp` constructor
            """
            
            FTP = ftplib.FTP_TLS if ssl is True else ftplib.FTP
            class FtpApp(FTP):
                
                def __init__(self):
                    print 'Init parent'
                    FTP.__init__(self, host)
                    
            return FtpApp()
            
        
        self.ftp = ftp()

    @property
    def currentdir(self):
        return self.ftp.pwd()
        
    def setLocalDir(self, localdir):
        self.localdir = localdir
        
        if not os.path.exists(self.localdir):
            os.makedirs(self.localdir)
    
    @Slot(bool)
    def checkout(self, download=True):
        """
        Recursively checks out all files on the server.
        Returns a dictionary of files on the server with their last modified date.
        
        :param download: Indicates whether or not the files should be downloaded
        """
        
        # Handy lists to keep track of the checkout process.
        # These lists contain absolute paths only.
        checked_dirs = list()
        checked_files = dict()

        # Sets '/' as initial directory and initializes `downloading_dir`
        self.cwd('/')
        downloading_dir = self.currentdir
            
        while True:
            # Gets the list of sub directories and files inside the 
            # current directory `downloading_dir`.
            dir_subdirs = self.getDirs(downloading_dir)
            dirfiles = self.getFiles(downloading_dir)
           
            # Leading '/' in `downloading_dir` breaks the `os.path.join` call
            localdir = os.path.join(self.localdir, downloading_dir[1:])
            if not os.path.exists(localdir):
                print 'Local dir: %s' % localdir
                # Creates the directory if it doesn't already exists.
                os.makedirs(localdir)

            for file_ in dirfiles:
                # `serverpath` is the absolute path of the file on the server,
                # download it only if it hasn't been already downloaded
                serverpath = os.path.join(downloading_dir, file_)
                if serverpath not in checked_files:
                    if download is True:
                        self.downloadFile(serverpath)
                    checked_files[serverpath] = self.lastModified(serverpath)
                        
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
                if self.currentdir == '/':
                    # All directories ready and at '/', means checkout is complete
                    break
                    
                else:
                    # Not at '/'. Current directory is ready so is appended to `checked_dirs`
                    # Back one directory to find directories that are not in `checked_dirs`
                    checked_dirs.append(downloading_dir)
                    downloading_dir = os.path.dirname(downloading_dir)
                    
        self.checkoutDone.emit(checked_files)
        return checked_files
                
    def getFiles(self, path):
        """
        This method simply wraps the `nlst` method with an exception handler,
        and returns an empty list in case an exception is caught.
        
        :param path: Relative or absolute path on the server
        """
        
        try:
            nlst = self.ftp.nlst(path)
            dirs = self.ftp.getDirs(path)
            
            # Files are items in nlst that are not in dirs
            files = [item for item in nlst if os.path.basename(item) not in dirs]
            
            return files
        except:
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
        
        self.ftp.retrlines('LIST %s' % path, handleLine)
        return dirs
        
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
            file_ = filename[1:] if filename.startswith('/') else filename
            localpath = os.path.join(self.localdir, file_)
        
        localdir = os.path.dirname(localpath)
        if not os.path.exists(localdir):
            # Creates the directory if it doesn't already exists.
            os.makedirs(localdir)
        
        with open(localpath, 'wb') as f:
            # Opens the file at `localname` which will hold the downloaded file.
            # Object attributes regarding download status are updated accordingly.
            print 'Downloading: %s' % filename
            self.downloadingFile.emit(filename)
            self.downloading = f
            self.download_size = int(self.sendcmd('SIZE %s' % filename).split(' ')[-1])
            self.download_progress = 0
            self.ftp.retrbinary('RETR %s' % filename, handleChunk)
            
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
        
    
if __name__ == '__main__':

    
    app3 = FtpObject('ops.osop.com.pa', False)
    app3.setLocalDir('/home/sergio/Documents/FTPSync/mareas')
    print app3.ftp.login('mareas', 'mareas123')
    
    print 'Dirs in "/": %s' % app3.getDirs('/')
    print 'Files in "/": %s' % app3.getFiles('/')

    app1 = FtpObject('ftp.iqstorage.com', True)
    app1.setLocalDir('/home/sergio/Documents/FTPSync/iq')
    app1.ftp.login('testuser', 'test')
    time = app1.lastModified('test2/2.15 MB Download.bin')
    print 'UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    print 'Dirs in "/": %s' % app1.getDirs('/')
    print 'Files in "/": %s' % app1.getFiles('/')

    app2 = FtpObject('10.18.210.193', False)
    app2.setLocalDir('/home/sergio/Documents/FTPSync/book')
    print app2.ftp.login('sergio', 'lopikljh')
    print 'Dirs in "/": %s' % app2.getDirs('/')
    print 'Files in "/": %s' % app2.getFiles('/')



    print 'Goin into event loop'

