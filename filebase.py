import datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean


dt = datetime.datetime
engine = create_engine('sqlite:///filestore.db', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()

class ActionQueue(object):
    
    def __init__(self):
        super(ActionQueue, self).__init__()
        
        self.session = Session()
        
    def __len__(self):
        return self.session.query(FileAction).count()
    
    def __getitem__(self, key):
        return self.session.query(FileAction).all()[key]
    
    def __iter__(self):
        return self.session.query(FileAction).__iter__()
    
    def __contains__(self, action):
        return session.query(FileAction).filter(path=action.path).count() > 1
    
    def remove(self, action):
        self.session.delete(action)
        self.session.commit()
    
    def add(self, action):
        # Looking for previous actions over the same path
        prev_action = self.session.query(FileAction).filter_by(path=action.path).first()
        if prev_action is not None:
            # If there is an action over the same path, update it
            prev_action.action = action.action
            prev_action.location = action.location
        else:
            self.session.add(action)
        self.session.commit()
        
    def next(self):
        nextaction = self.session.query(FileAction).first()
        
        return nextaction
    
    def __repr__(self):
        return self.session.query(FileAction).all().__repr__()
    
    
class FileAction(Base):
    
    __tablename__ = 'actions'
    id = Column(Integer, primary_key=True)
    path = Column(String)
    action = Column(String)
    location = Column(String)
    
    UPLOAD = 'upload'
    DOWNLOAD = 'download'
    DELETE = 'delete'
    
    SERVER = 'server'
    LOCAL = 'local'
    
    def __init__(self, path, action, location):
        
        self.path = path
        self.action = action
        self.location = location

    def __repr__(self):
        return '<FileAction in %s ("%s" "%s" to "%s")>' % (
                self.__tablename__, self.action, self.path, self.location)

        
class File(Base):
    
    __tablename__ = 'files'
    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True)
    localmdate = Column(DateTime)
    servermdate = Column(DateTime)
    last_checked_local = Column(DateTime) 
    last_checked_server = Column(DateTime)
    inserver = Column(Boolean)
    inlocal = Column(Boolean)
    
    def __init__(
            self, path='', localmdate=None, servermdate=None,
            last_checked_local=None, last_checked_server=None, 
            inserver=False, inlocal=False):
        
        self.path = path
        self.localmdate = localmdate
        self.servermdate = servermdate
        self.last_checked_local = last_checked_local
        self.last_checked_server = last_checked_server
        self.inserver = inserver
        self.inlocal = inlocal
        
    def __repr__(self):
        return '<File in %s ("%s", Local: "%s", Server: "%s")>' % (
                    self.__tablename__, self.path, self.inlocal, self.inserver)
        
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.session.commit()
        
    @classmethod
    def fromPath(cls, path):
        """
        Returns a `File` instance by fetching it from the database
        using the `path` parameter, if such entry doesn't exist, this
        function adds it to the database and returns the added instance.
        
        :param path: `path` attribute of the `File` instance that will be fetched.
        """
        
        session = Session()
        try:
            newfile = session.query(cls).filter_by(path=path).one()
            newfile.session = session
            return newfile
        except MultipleResultsFound:
            print 'More than one result for "%s", database might be corrupted' % path
            return None
        except NoResultFound:
            newfile = File(path)
            session.add(newfile)
            newfile.session = session
            return newfile
            

Base.metadata.create_all(engine)

if __name__ == '__main__':
    session = Session()
    localfile = File.fromPath('Public/Something')
    print localfile.inserver
    localfile.inserver = True
    
    myfile = File.fromPath('Public/New')
    print myfile.last_checked_local, myfile.last_checked_server, myfile.inlocal, myfile.inserver
    
    serverfile = File.fromPath('Public/Something/Else')
    print serverfile.inlocal
    serverfile.inlocal = True
    
    otherfile = File.fromPath('Public/Other/File')
    print otherfile
    otherfile.inlocal = True
    otherfile.inserver = True
    print otherfile.inlocal, otherfile.inserver
    
    for file_ in session.query(File):
        print file_


    print dir(session.query())

    action_queue = ActionQueue()
    action = FileAction('/some/path', FileAction.UPLOAD, FileAction.SERVER)
    
    action_queue.add(action)
    print action_queue
    print action_queue[0]
    print action_queue.next()
    
    
    for action_ in action_queue:
        print action_
        
    session.commit()
    
