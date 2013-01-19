#ifndef SYNCAPP_H
#define SYNCAPP_H

#include <QFtp>

#include "global.h"

class LocationItem;

class SyncApp : public QFtp
{
    Q_OBJECT

public:

    // Public Methods

    explicit SyncApp(QObject *parent = 0);
    
    explicit SyncApp(const QString & hostname, QObject *parent = 0);

    ~SyncApp();

    void setHostname(const QString & hostname);

    QString hostname() const;

    QString username() const;

    QString password() const;

private:

    // Private Members

    QList<LocationItem> dirItems;

    QList<LocationItem> doneItems;

    int lsId;

    int stepsToHome;

    QString sessionHost;

    QString sessionUser;

    QString sessionPassword;

    // Private Methods

    void init();

signals:

public slots:

    void requestLogin(const QString & username, const QString & password);
    
private slots:

    void finished(int commandId, bool success);

    void ready(bool error);

    void receiveUrl(const QUrlInfo & urlInfo);
};

/////////////////////////////////////////////////////////////////////////////////////

class LocationItem {

public:

    enum Type {File, Directory};

    LocationItem(const QString & path, Type type);

    QString path() const;

    Type type() const;

    QString typeString() const;

    friend QDebug operator<< (QDebug d, const LocationItem & item);

private:

    QString locationPath;

    Type locationType;
};

#endif // SYNCAPP_H
