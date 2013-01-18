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
}


// Public Slots

void SyncApp::requestLogin(const QString &username, const QString &password)
{
    if (sessionHost.isEmpty())
        return;

    connectToHost(sessionHost);
    login(username, password);
    list();

    sessionUser = username;
    sessionPassword = password;
}

// Private Slots

void SyncApp::ready(bool error)
{
    qDebug() << "Ready: " << !error << errorString() << state();
}

void SyncApp::receiveUrl(const QUrlInfo & urlInfo)
{
    qDebug() << "Url Name ->" << urlInfo.name();
    qDebug() << "Url Owner ->" << urlInfo.owner();
    qDebug() << "Url Group ->" << urlInfo.group();
    qDebug() << "Url Last Mod ->" << urlInfo.lastModified();
    qDebug() << "Url Directory ->" << urlInfo.isDir();
}
