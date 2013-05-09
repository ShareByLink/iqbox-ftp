from abc import ABCMeta, abstractmethod

import socket

from datetime import datetime as dt
from datetime import timedelta as td
from ftplib import FTP_TLS, FTP, error_reply, error_perm
 
class filetransfer_abc:
    __metaclass__ = ABCMeta
 
    @abstractmethod
    def do_something(self): pass

    @abstractmethod
    def connect(self): pass
 
 
class ftp_si(filetransfer_abc):

    username = ''
    passwd = ''
    ftp = None
    
    
    def do_mystuff(self):
        print "Do my stuff!"
    def do_something(self):
        print "Do something!"

    def __init__(self, host, useSSL):
        
        self.ftp = None
        self.useSSL = useSSL
        self.host = host
        useSSL = False

    def connect(self, the_user, the_passwd):

        self.username = the_user
        self.passwd = the_passwd
        
        ok=True
        msg = ''

        if self.useSSL is True:
            self.ftp = FTP_TLS(self.host)
        else:    
            self.ftp=FTP(self.host)
        

        try:        
            loginResponse = self.ftp.login(self.username, self.passwd)
            msg = 'Login ok'
        except socket.gaierror:
            self.ftp = None
            ok = False
            msg = 'Server address could not be found.' 
        except (error_perm, error_reply):
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            ok = False
            msg = error_msg         
        else:
            if '230' in loginResponse:
                ok = True
            else:
                ok = False
                msg = error_msg
        
        return msg
                
    def setdir(self, path):
        self.ftp.cwd(path)

    @property
    def currentdir(self):
        """Returns the current working directory at the server"""
        
        return self.ftp.pwd()         
    
    def listfiles_basic(self, path):
        return self.ftp.nlst(path)

    def listfiles_ftpdetails(self, path, callback_function):
        
        try:
            self.ftp.retrlines('LIST %s' % path, callback_function)
            
            return
        except:
            print 'Exception in ServerWatcher.getDirs'
            info = traceback.format_exception(*sys.exc_info())
            for i in info: sys.stderr.write(i)
            return []    

    def deleteFile(self, filename):
        """
        Deletes the file `filename` to the server
        
        :param filename: Absolute or relative path to the file
        """
        
        try:
            # print 'Deleting %s' % filename
            self.ftp.delete(filename)
            return True
        except (error_reply, error_perm):
            # print 'Error deleting %s' % filename
            return False


    def fileExists(self, filepath):
        try:
            self.ftp.sendcmd('SIZE %s' % filepath)
        except (error_reply, error_perm):
            exists = False
        else:
            exists = True


    
    def fileSize (self, filename):

        try:        
            download_size = int(self.ftp.sendcmd('SIZE %s' % filename).split(' ')[-1])

        except (IOError, OSError):
            download_size = -1
            # self.ioError.emit(localpath)
        except (error_reply, error_perm) as ftperr:
            # print 'Error downloading %s, %s' % (filename, ftperr)
            download_size = -1
        
        return download_size
    
    
    def downloadFile(filename, callback_function):
        downloaded = True
        
        try:
            self.ftp.retrbinary('RETR %s' % filename, handleChunk)
        except (IOError, OSError):
            downloaded = False
            # self.ioError.emit(localpath)
        except (error_reply, error_perm) as ftperr:
            # print 'Error downloading %s, %s' % (filename, ftperr)
            downloaded = False    
        
        return downloaded


    def uploadFile (self, filename, callback_function):
        
        try:
            # Uploads file and updates its modified date in the server
            # to match the date in the local filesystem.
            self.upload_progress = 0
            self.upload_size = os.path.getsize(localpath)
            # self.fileEvent.emit(localpath)
            self.ftp.storbinary('STOR %s' % filename,
                                open(localpath, 'rb'), 
                                1024,
                                handle)
            # print 'Upload finished'
            with File.fromPath(filename) as uploaded:
                modified = uploaded.localmdate
                uploaded.servermdate = modified
                
                self.setLastModified(filename, modified)
            
            uploaded = True

        except (IOError, OSError):
            uploaded = False
            self.ioError.emit(localpath)
        except (error_reply, error_perm, OSError) as err:
            print 'Error uploading %s, %s' % (filename, err)
            uploaded = False
                    
        
    def lastModified(self, filename):
        """
        Uses the MDTM FTP command to find the last modified timestamp
        of the file `filename`.
        Returns a `datetime.datetime` object in UTC representing the file's
        last modified date and time.
        
        :param filename: Relative or absolute path to the file
        """
        
        timestamp = self.ftp.sendcmd('MDTM %s' % filename)
        if '213 ' not in timestamp:
            # Second chance was found to be needed in some cases.
            timestamp = self.ftp.sendcmd('MDTM %s' % filename)

        timestamp = timestamp.split(' ')[-1]
        dateformat = '%Y%m%d%H%M%S.%f' if '.' in timestamp else '%Y%m%d%H%M%S'
        
        try:
            mtime = dt.strptime(timestamp, dateformat)
        except ValueError:
            mtime = dt.utcnow()

        return mtime

    def setLastModified(self, serverpath, newtime):
        """
        Uses the MFMT or MDTM FTP commands to set `newtime` as the modified timestamp of the
        file `serverpath` on the server. 

        :param serverpath: Relative or absolute path to the file
        :param newtime: datedatime object holding the required time
        """
        cmds = ['MFMT', 'MDTM']
        for cmd in cmds:
            try:
                self.ftp.sendcmd(
                        '%s %s %s' % (cmd, newtime.strftime('%Y%m%d%H%M%S'), serverpath))
                return
            except (error_perm, error_reply) as e:
                if cmd == cmds[len(cmds) - 1]:
                    # If is the last comand, re-raise the exception, else
                    # keep trying.
                    raise e
                else:
                    continue
        
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

    
if __name__ == '__main__':
    
    print "hello"
    c = ftp_si('ftp.iqstorage.com', True)
    c.connect('testuser', 'test')

    a = list
    a = c.listfiles_basic('/')
    print a
    
    #for s in a:
    #    print s
        
    print "Done"
    #c.do_something()
    #c.do_mystuff()
    