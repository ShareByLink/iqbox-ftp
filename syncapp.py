import ftplib


class SyncApp(ftplib.FTP_TLS):

    def __init__(self, host, user, passwd):
        ftplib.FTP_TLS.__init__(self, host, passwd)


