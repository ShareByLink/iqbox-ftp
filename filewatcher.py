import os
import sys
import datetime
import traceback


dt = datetime.datetime


class FileWatcher(object):
    
    def __init__(self, localdir):
        self.localdir = localdir
        
    def checkout(self):
        print os.walk()
        

if __name__ == '__main__':
    checked_files = dict()
    for item in os.walk('/home/sergio/Documents/FTPSync/'):
        directory = item[0]
        subfiles = item[-1]
        for file_ in subfiles:
            filepath = os.path.join(directory, file_)
            checked_files[filepath] = dt.utcfromtimestamp(os.path.getmtime(filepath))
            
    print checked_files
