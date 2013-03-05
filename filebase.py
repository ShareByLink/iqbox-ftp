import datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean


dt = datetime.datetime
engine = create_engine('sqlite:///filestore.db', echo=False)
Session = sessionmaker(bind=engine)
Base = declarative_base()
session = Session()


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
                    self.__tablename__, self.path, self.inlocatl, self.inserver)
        
    @classmethod
    def getFile(cls, path):
        """
        Returns a `File` instance by fetching it from the database
        using the `path` parameter, if such entry doesn't exist, this
        function adds it to the database and returns the added instance.
        
        :param path: `path` attribute of the `File` instance that will be fetched.
        """
        
        session.commit()
        try:
            newfile = session.query(cls).filter_by(path=path).one()
            return newfile
        except MultipleResultsFound:
            print 'More than one result for "%s", database might be corrupted' % path
            return None
        except NoResultFound:
            newfile = File(path)
            session.add(newfile)
            return newfile


Base.metadata.create_all(engine)

if __name__ == '__main__':
    localfile = File.getFile('Public/Something')
    print localfile.inserver
    localfile.inserver = True
    
    myfile = File.getFile('Public/New')
    print myfile.last_checked_local, myfile.last_checked_server, myfile.inlocal, myfile.inserver
    
    serverfile = File.getFile('Public/Something/Else')
    print serverfile.inlocal
    serverfile.inlocal = True
    
    otherfile = File.getFile('Public/Other/File')
    print otherfile
    otherfile.inlocal = True
    otherfile.inserver = True
    print otherfile.inlocal, otherfile.inserver
    

    print session.query(File).all()
    
    
    session.commit()
    
