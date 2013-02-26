import os
import ftplib
import datetime


dt = datetime.datetime


class SyncApp(ftplib.FTP_TLS):

    def __init__(self, host, localpath):
        ftplib.FTP_TLS.__init__(self, host)
        
        self.localpath = localpath
        
        if not os.path.exists(self.localpath):
            os.makedirs(self.localpath)
        
    def checkout(self):
        """
        Syncronizes all files on the server by recursively downloading the files.
        Any local files will be truncated.
        """
        
    def getDirs(self, path):
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
        
    def getFile(self, file):
        """
        Performs a binary download to the file `file` located on the server.
        `file` parameter can be either absolute or relative, though it can
        fail for relative paths if the current directory is not appropiate.
        
        :param filename: Relative or absolute path to the file
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
        
        # Gets the absolute local file path corresponding to the file `file`
        localname = os.path.join(self.localpath, os.path.basename(file))
        with open(localname, 'wb') as f:
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
        Returns a `datetime.datetime` UTC object representing the file's
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
    #app.getFile('test2/2.15 MB Download.bin')
    print 'Dirs in "/": %s' % app.getDirs('/')
    print 'Dirs in "/test2": %s' % app.getDirs('/test2')
    print 'Files in "/": %s' % app.nlst('/')
    print 'Files in "/test2": %s' % app.nlst('/test2')

