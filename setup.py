import sys
from cx_Freeze import setup, Executable

includefiles = ['key']
includemodules = ['sqlite3', 'sqlalchemy', 'sqlalchemy.dialects.sqlite']

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

setup(name = 'IQBox',
      version = '0.1',
      description = 'FTP Sync application',
      options = {'build_exe': {'include_files': includefiles, 'includes': includemodules}},
      executables = [Executable("syncview.py", base=base)])
