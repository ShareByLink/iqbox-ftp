import datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from PySide.QtCore import QObject

dt = datetime.datetime
engine = create_engine('sqlite:///filestore.db', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()
session = Session()

SERVER = 'server'
SERVER_TEMP = 'server_temp'
LOCAL = 'local'
LOCAL_TEMP = 'local_temp'

CLASS_NAMES = dict(
    server='ServerFile',
    server_temp='ServerTempFile',
    local='LocalFile',
    local_temp='LocalTempFile')

_created = dict()

def clear_server_temp():
    session.query(getFile(SERVER_TEMP).__class__).delete()

def getFile(location, *args):
    
    if location in _created:
        return _created[location].__call__(*args)
    
    __tablename__ = location
    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True)
    mdate = Column(DateTime)
    
    def __init__(self, path='', mdate=None):
        self.path = path
        self.mdate = mdate
        
    def __repr__(self):
        return '<File in %s ("%s", "%s")>' % (
                    self.__tablename__, self.path, self.mdate)
         
    def exists(self):
        try:
            session.query(self.__class__).filter(self.__class__.path == self.path).one()
            return True
        except MultipleResultsFound:
            print 'More than one result for "%s", database might be courrupted' % self.path
            return True
        except NoResultFound:
            return False
            
    def save(self):
        try:
            session.add(self)
            print self
            return True
        except IntegrityError:
            return False
    
    cls = CLASS_NAMES[location]
    
    file_attrs = dict(
        id=id, path=path, mdate=mdate, save=save, __init__=__init__,
        __repr__=__repr__, exists=exists, __tablename__=__tablename__)
    
    File = type(cls, (Base,), file_attrs)
    _created[location] = File
    
    return File(*args)

Base.metadata.create_all(engine)

if __name__ == '__main__':
    serverfile = getFile(SERVER, '/Public/test.txt', dt.utcnow())
    print serverfile.exists()

    localfile = getFile(LOCAL, '/home/sergio/test2.txt', dt.utcnow())
    print localfile.exists()
   
    print serverfile.metadata.tables
    
    print session.query(serverfile.__class__).all()
    print session.query(localfile.__class__).all()
    print session.query(serverfile.__class__).all()
    
    
    session.commit()
    
