import os
import ftplib
import datetime


dt = datetime.datetime


class SyncApp(ftplib.FTP_TLS):
    """Extending the`ftplib.FTP_TLS` class"""

    def __init__(self, host, localdir):
        ftplib.FTP_TLS.__init__(self, host)
        
        self.localdir = localdir
        
        if not os.path.exists(self.localdir):
            os.makedirs(self.localdir)
    
    @property
    def currentdir(self):
        return self.pwd()
        
    def checkout(self):
        """
        Syncronizes all files on the server by recursively downloading the files.
        Any local files will be truncated.
        """
        
        # Handy variables to keep track of the checkout process.
        # These lists contain absolute paths only.
        checked_dirs = list()
        downloaded = list()

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
                # Creates the directory if it doesn't already exists.
                os.makedirs(localdir)

            for file in dirfiles:
                # `serverpath` is the absolute path of the file on the server,
                # download it only if it hasn't been already downloaded
                serverpath = os.path.join(downloading_dir, file)
                if serverpath not in downloaded:
                    # Downloads the file and appends it absolute path to the `downloaded` list
                    self.downloadFile(serverpath)
                    downloaded.append(serverpath)
                    
            dir_ready = True
            for dir in dir_subdirs:
                # `dirpath` is the absolute path of the subdirectory on the server,
                dirpath = os.path.join(downloading_dir, dir)
                
                # `downloading_dir` is ready only when all its subdirectory are on the 
                # `checked_dirs` list.
                if dirpath not in checked_dirs:
                    # Found one subdirectory that is not on `checked_dirs`,
                    # will process it in the next iteration.
                    downloading_dir = dirpath
                    dir_ready = False
                    
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
                
    def getFiles(self, path):
        """
        This method simply wraps the `nlst` method with an exception handler,
        and returns an empty list in case an exception is caught.
        
        :param path: Relative or absolute path on the server
       """
        try:
            return self.nlst(path)
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
                dirname = line.split(' ')[-1]
                if dirname != '.' and dirname != '..':
                    # Ignoring '.' and '..' entries
                    dirs.append(dirname)
        
        self.retrlines('LIST %s' % path, handleLine)
        return dirs
        
    def downloadFile(self, file, localpath=None):
        """
        Performs a binary download to the file `file` located on the server.
        `file` parameter can be either absolute or relative, though it can
        fail for relative paths if the current directory is not appropiate.
        
        :param filename: Relative or absolute path to the file
        :param localpath: Absolute local path where the file will be saved
        """
        
        def handleChunk(chunk):
            """
            Recieves chuncks of data downloaded from the server.
            This function is meant to be used as callback for the `retrbinary` method.
            
            :params chunk: Chunk of downloaded bytes to be written into the file
            """
        
            # Simply writes the recieved data into the file `self.downloading`
            self.downloading.write(chunk)
            self.download_total += len(chunk)
        
        
        if localpath is None:
            # Gets the absolute local file path corresponding to the file `file`
            # removing '/' at the beginnig of `file` so the `os.path.join` call works
            file_ = file[1:] if file.startswith('/') else file
            localpath = os.path.join(self.localdir, file_)
        
        localdir = os.path.dirname(localpath)
        if not os.path.exists(localdir):
            # Creates the directory if it doesn't already exists.
            os.makedirs(localdir)
        
        with open(localpath, 'wb') as f:
            # Opens the file at `localname` which will hold the downloaded file.
            # Object attributes regarding download status are updated accordingly.
            self.downloading = f
            self.download_size = int(self.sendcmd('SIZE %s' % file).split(' ')[-1])
            self.download_total = 0
            self.retrbinary('RETR %s' % file, handleChunk)
            
    def lastModified(self, file):
        """
        Uses the MDTM FTP command to find the last modified timestamp
        of the file `filename`.
        Returns a `datetime.datetime` object in UTC representing the file's
        last modified date and time.
        
        :param filename: Relative or absolute path to the file
        """
        
        timestamp = self.sendcmd('MDTM %s' % file)
        timestamp = timestamp.split(' ')[-1]
        format = '%Y%m%d%H%M%S.%f' if '.' in timestamp else '%Y%m%d%H%M%S'
        
        return dt.strptime(timestamp, format)


if __name__ == '__main__':
    app = SyncApp('ftp.iqstorage.com', '/home/sergio/Documents/FTPSync')
    
    app.login('testuser', 'test')
    time = app.lastModified('test2/2.15 MB Download.bin')
    print 'UTC: %s, Local: %s' % (time, time - datetime.timedelta(hours=5))
    print 'Dirs in "/": %s' % app.getDirs('/')
    print 'Dirs in "/test2": %s' % app.getDirs('/test2')
    print 'Files in "/": %s' % app.nlst('/')
    print 'Files in "/test2": %s' % app.nlst('/test2')
    
    app.checkout()

