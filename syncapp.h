#ifndef SYNCAPP_H
#define SYNCAPP_H

#include <QFtp>
#include <QFile>

#include "global.h"

class LocationItem {

public:

    enum Type {File, Directory, Undefined};

    LocationItem();

    LocationItem(const QString & path, const QString & name, Type type);

    QString name() const;

    QString path() const;

    Type type() const;

    QString typeString() const;

    friend QDebug operator<< (QDebug d, const LocationItem & item);

    friend bool operator== (const LocationItem & rhs, const LocationItem & lhs);

private:

    QString locationName;

    QString locationPath;

    Type locationType;
};

/////////////////////////////////////////////////////////////////////////////////////

class SyncApp : public QFtp
{
    Q_OBJECT

public:

    // Public Methods

    explicit SyncApp(QObject *parent = 0);
    
    explicit SyncApp(const QString & hostname, QObject *parent = 0);

    ~SyncApp();

    QString hostname() const;

    QString localPath() const;

    QString password() const;

    void setHostname(const QString & hostname);

    void setLocalPath(const QString & localPath);

    QString username() const;

private:

    // Private Members

    LocationItem currentDirItem;

    QString currentDirPath;

    QList<LocationItem> dirItems;

    int dlId;

    QList<LocationItem> doneItems;

    QList<LocationItem> downloading;

    int lsId;

    int stepsToHome;

    QString sessionHost;

    QString sessionUser;

    QString sessionPassword;

    QString sessionPath;

    int toHome;

    // Private Methods

    void changeDirectory(const LocationItem & directory);

    void downloadNext();

    void goBack();

    void init();

    void updateAll();

signals:

    void loggedIn(bool ok);

public slots:

    void requestLogin(const QString & username, const QString & password);
    
private slots:

    void finished(int commandId, bool commandError);

    void ready(bool commandError);

    void receiveUrl(const QUrlInfo & urlInfo);
};

#endif // SYNCAPP_H
