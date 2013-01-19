#include "syncapp.h"

// Public Methods

SyncApp::SyncApp(QObject *parent) :
    QFtp(parent)
{
    init();
}

SyncApp::SyncApp(const QString & hostname, QObject *parent) :
    QFtp(parent)
{
    init();
    setHostname(hostname);
}

void SyncApp::setHostname(const QString &hostname)
{
    sessionHost = hostname;
}

SyncApp::~SyncApp()
{
}


QString SyncApp::hostname() const
{
    return sessionHost;
}

QString SyncApp::username() const
{
    return sessionUser;
}

QString SyncApp::password() const
{
    return sessionPassword;
}

// Private Methods

void SyncApp::init()
{
    connect(this, SIGNAL(done(bool)), this, SLOT(ready(bool)));
    connect(this, SIGNAL(listInfo(QUrlInfo)), this, SLOT(receiveUrl(QUrlInfo)));
    connect(this, SIGNAL(commandFinished(int,bool)), this, SLOT(finished(int,bool)));
}


// Public Slots

void SyncApp::requestLogin(const QString &username, const QString &password)
{
    if (sessionHost.isEmpty())
        return;

    connectToHost(sessionHost);
    login(username, password);
    lsId = list();

    sessionUser = username;
    sessionPassword = password;
}

// Private Slots

void SyncApp::finished(int commandId, bool success)
{
    if (commandId == lsId) {
        qDebug() << "Finished list:" << success << dirItems;
    }
}

void SyncApp::ready(bool error)
{
    qDebug() << "Ready: " << !error << errorString() << state();
}

void SyncApp::receiveUrl(const QUrlInfo & urlInfo)
{
    QString path = urlInfo.name();
    LocationItem::Type type = urlInfo.isDir() ?
                LocationItem::Directory : LocationItem::File;

    dirItems.append(LocationItem(path, type));

    /*
    qDebug() << "Url Name ->" << urlInfo.name();
    qDebug() << "Url Owner ->" << urlInfo.owner();
    qDebug() << "Url Group ->" << urlInfo.group();
    qDebug() << "Url Last Mod ->" << urlInfo.lastModified();
    qDebug() << "Url Directory ->" << urlInfo.isDir();
    */
}

////////////////////////////////////////////////////////////////////////////////////

LocationItem::LocationItem(const QString & path, Type type)
{
    locationPath = path;
    locationType = type;
}

QString LocationItem::path() const
{
    return locationPath;
}

LocationItem::Type LocationItem::type() const
{
    return locationType;
}

QString LocationItem::typeString() const
{
    QString typeString;

    switch(type()) {
    case File:
        typeString = "File";
        break;

    case Directory:
        typeString = "Directory";
        break;

    default:
        typeString = "Undefined";
    }

    return typeString;
}

QDebug operator<< (QDebug d, const LocationItem & item) {
    d << (item.path() + " - " + item.typeString());
    return d;
}
