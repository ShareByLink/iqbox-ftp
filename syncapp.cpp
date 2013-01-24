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

    lsId = list(directory.path());
}

void SyncApp::downloadNext()
{

    if (!downloading.isEmpty()) {
        QString nextFile = downloading.at(0).path();
        dlId = get(nextFile);
        emit downloadingFile(nextFile);
    }
}

void SyncApp::goBack()
{
    toHome--;

    QStringList steps = currentDirItem.path().split("/", QString::SkipEmptyParts);
    QString prevPath;
    for (int i = 0; i < steps.size() - 1; i++)
        prevPath += steps.at(i) + "/";
    QString prevName = steps.size() <= 1 ? "" : steps.at(steps.size() - 2);

    currentDirItem = LocationItem(prevPath, prevName, LocationItem::Directory);
    currentDirPath = prevPath;
    dirItems.clear();
    downloading.clear();

    lsId = list(currentDirItem.path());
}

void SyncApp::init()
{
    toHome = 0;

    connect(this, SIGNAL(listInfo(QUrlInfo)), this, SLOT(receiveUrl(QUrlInfo)));
    connect(this, SIGNAL(commandFinished(int,bool)), this, SLOT(finished(int,bool)));
}

void SyncApp::updateAll()
{
    // Main method for recursive download.
    if (downloading.isEmpty()) {
        // Finished downloading current directory.
        bool dirReady = true;
        LocationItem item;
        foreach (item, dirItems) {
            if (item.type() == LocationItem::Directory && !doneItems.contains(item)) {
                // Found a directory that is not in 'doneItems', will check it up.
                dirReady = false;
                changeDirectory(item);
                break;
            }
        }

        // All items in the current directory are in 'doneItems',
        // and all files have been downloaded as the list 'downloading' is empty.
        if (dirReady) {
            if (toHome == 0) {
                // If home directory is finished, that is it.
                abort();
                qDebug() << "Finished" << currentCommand();
                lsId = 0;
                emit finishedDownload();
                return;
            }

            else {
                // Not in home, going back looking for
                // items in previous directory.
                addDoneItem(currentDirItem);
                goBack();
            }
        }
    }

    // Keep downloading all files until
    // the list is empty.
    else {
        downloadNext();
    }
}

// Public Slots

void SyncApp::requestDownload()
{
    lsId = list();
}

void SyncApp::requestLogin(const QString &username, const QString &password)
{
    if (sessionHost.isEmpty())
        return;

    connectToHost(sessionHost);
    logId = login(username, password);

    sessionUser = username;
    sessionPassword = password;
}

// Private Slots

void SyncApp::finished(int commandId, bool commandError)
{
    if (commandId == lsId) {
        // Finished list lookup, 'dirItems' is now filled only with
        // the items in the current directory.
        qDebug() << "Current Dir Item:" << currentDirItem;
        qDebug() << "Current Dir Path:" << currentDirPath;

        // Finds out the local path for the corresponding
        // to the corrent directory, and creates it in local
        // filesystem if it doesn't exist.
        QString dirPath = sessionPath + currentDirPath;
        if (!QDir(dirPath).exists())
            QDir().mkpath(dirPath);

        // Checking up what items in the current directory
        // are Files that need downloading.
        LocationItem item;
        foreach (item, dirItems) {
            if (item.type() == LocationItem::File && !doneItems.contains(item))
                downloading.append(item);
        }

        // Calls the method *almost* recursively.
        updateAll();
    }

    else if (commandId == dlId) {
        // Finished downloading a file, saving it
        // to the local filesystem in the right path.
        if (!downloading.isEmpty()) {
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

                // Calls the method *almost* recursively.
                updateAll();
            }
        }

        else {
            qDebug() << "Error Downloading:" << error() << errorString();
        }
    }

    else if (commandId == logId) {
        if (!commandError) {
            currentDirPath = "";
        }

        else {
            close();
        }


        emit loggedIn(!commandError);
    }
}

void SyncApp::receiveUrl(const QUrlInfo & urlInfo)
{
    // This method is called when getting the list
    // of the current directory.
    // It receives each item in the curreny directory one by one.
    QString path = currentDirPath + urlInfo.name();

    LocationItem::Type type = urlInfo.isDir() ?
                LocationItem::Directory : LocationItem::File;

    dirItems.append(LocationItem(path, urlInfo.name(), type));
}
