#include <QStringList>
#include <QDir>

#include "syncapp.h"

LocationItem::LocationItem()
{
    locationPath = "";
    locationType = Undefined;
    locationName = "";
}

LocationItem::LocationItem(const QString & path, const QString &name, Type type)
{
    locationPath = path;
    locationType = type;
    locationName = name;
}

QString LocationItem::name() const
{
    return locationName;
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
    d << (item.path() + " - " + item.name() + " - " + item.typeString());
    return d;
}

bool operator== (const LocationItem & rhs, const LocationItem & lhs)
{
    if (rhs.type() == lhs.type() &&
        rhs.path() == lhs.path())
        return true;

    else
        return false;
}

////////////////////////////////////////////////////////////////////////////////////

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

SyncApp::~SyncApp()
{
}


QString SyncApp::hostname() const
{
    return sessionHost;
}

QString SyncApp::localPath() const
{
    return sessionPath;
}

QString SyncApp::password() const
{
    return sessionPassword;
}

void SyncApp::setHostname(const QString &hostname)
{
    sessionHost = hostname;
}

void SyncApp::setLocalPath(const QString &localPath)
{
    sessionPath = localPath;

    if (!sessionPath.endsWith(QDir::separator()))
        sessionPath += QDir::separator();
}

QString SyncApp::username() const
{
    return sessionUser;
}


// Private Methods

void SyncApp::addDoneItem(const LocationItem &item)
{
    if (!doneItems.contains(item))
        doneItems.append(item);
}

void SyncApp::changeDirectory(const LocationItem & directory)
{
    toHome++;
    currentDirItem = directory;
    dirItems.clear();
    downloading.clear();
    if (!currentDirItem.path().isEmpty())
        currentDirPath.append(currentDirItem.name() + QDir::separator());

    cd(directory.name());
    lsId = list();
}

void SyncApp::downloadNext()
{
    /*
    if (!downloading.isEmpty())
        dlId = get(downloading.at(0).name());
    */
    bool commandError = false;
    if (!downloading.isEmpty()) {
        LocationItem newItem = downloading.takeFirst();
        addDoneItem(newItem);
        if (!commandError) {
            QString filePath = sessionPath + newItem.path();
            QString dirPath = filePath.section(QDir::separator(), 0, -2);

            if (!QDir(dirPath).exists())
                QDir().mkpath(dirPath);

            QFile newFile(filePath);
            newFile.open(QFile::WriteOnly | QFile::Truncate);
            newFile.write("Hello");
            newFile.close();

            updateAll();
        }
    }
}

void SyncApp::goBack()
{
    toHome--;

    QStringList steps = currentDirItem.path().split("/", QString::SkipEmptyParts);
    QString prevPath;
    for (int i = 0; i < steps.size() - 1; i++)
        prevPath += steps.at(i) + "/";
    QString prevName = steps.at(steps.size() - 2);

    currentDirItem = LocationItem(prevPath, prevName, LocationItem::Directory);
    currentDirPath = prevPath;
    dirItems.clear();
    downloading.clear();

    cd("..");
    lsId = list();
}

void SyncApp::init()
{
    toHome = 0;

    connect(this, SIGNAL(done(bool)), this, SLOT(ready(bool)));
    connect(this, SIGNAL(listInfo(QUrlInfo)), this, SLOT(receiveUrl(QUrlInfo)));
    connect(this, SIGNAL(commandFinished(int,bool)), this, SLOT(finished(int,bool)));
}

void SyncApp::updateAll()
{
    if (downloading.isEmpty()) {
        bool dirReady = true;
        LocationItem item;
        foreach (item, dirItems) {
            if (item.type() == LocationItem::Directory && !doneItems.contains(item)) {
                dirReady = false;
                changeDirectory(item);
                break;
            }
        }

        if (dirReady) {
            if (toHome == 0) {
                // Finished!
            }

            else {
                addDoneItem(currentDirItem);
                goBack();
            }
        }
    }

    else {
        downloadNext();
    }
}

// Public Slots

void SyncApp::requestLogin(const QString &username, const QString &password)
{
    if (sessionHost.isEmpty())
        return;

    connectToHost(sessionHost);
    login(username, password);
    updateAll();

    sessionUser = username;
    sessionPassword = password;
}

// Private Slots

void SyncApp::finished(int commandId, bool commandError)
{
    if (commandId == lsId) {

        qDebug() << "Current Dir Item:" << currentDirItem;
        qDebug() << "Current Dir Path:" << currentDirPath;

        QString dirPath = sessionPath + currentDirPath;

        if (!QDir(dirPath).exists())
            QDir().mkpath(dirPath);

        LocationItem item;
        foreach (item, dirItems) {
            if (item.type() == LocationItem::File && !doneItems.contains(item))
                downloading.append(item);
        }

        updateAll();
    }

    else if (commandId == dlId) {
        LocationItem newItem = downloading.takeFirst();
        doneItems.append(newItem);
        if (!commandError) {
            QString filePath = sessionPath + newItem.path();
            QString dirPath = filePath.section(QDir::separator(), 0, -2);

            if (!QDir(dirPath).exists())
                QDir().mkpath(dirPath);

            QFile newFile(filePath);
            newFile.open(QFile::WriteOnly | QFile::Truncate);
            newFile.write(readAll());
            newFile.close();

            updateAll();
        }

        else {
            qDebug() << "Error Downloading:" << error() << errorString();
        }
    }
}

void SyncApp::ready(bool commandError)
{
    qDebug() << "Ready: " << !commandError << errorString() << state() << currentCommand();

    if (!commandError) {
        switch(state()) {
        case SyncApp::LoggedIn:
            emit loggedIn(true);
            lsId = list();
            currentDirPath = "";
            break;

        default:
            qDebug() << state();
            break;
        }
    }

    else {
        switch(error()) {
        case SyncApp::ConnectionRefused: case SyncApp::UnknownError:
            close();
            emit loggedIn(false);
            break;

        default:
            qDebug() << error();
            break;
        }

    }
}

void SyncApp::receiveUrl(const QUrlInfo & urlInfo)
{
    QString path = currentDirPath + urlInfo.name();

    LocationItem::Type type = urlInfo.isDir() ?
                LocationItem::Directory : LocationItem::File;

    dirItems.append(LocationItem(path, urlInfo.name(), type));
}
