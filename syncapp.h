#ifndef SYNCAPP_H
#define SYNCAPP_H

#include <QFtp>

#include "global.h"

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

    void ready(bool error);

    void receiveUrl(const QUrlInfo & urlInfo);
};

#endif // SYNCAPP_H
