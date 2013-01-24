#include <QStatusBar>

#include "syncwindow.h"

// Public Methods

SyncWindow::SyncWindow(QWidget *parent) :
    QMainWindow(parent)
{
    loginView = new SyncLogin;
    syncView = new SyncScreen;
    sync = new SyncApp;
    syncIcon = new QSystemTrayIcon(this);

    syncIcon->setIcon(QIcon(QPixmap(":resources/icon.png")));
    syncIcon->show();

    connect(loginView, SIGNAL(login(QString,QString,QString)), this, SLOT(loginRequested(QString,QString,QString)));
    connect(sync, SIGNAL(loggedIn(bool)), this, SLOT(loginResult(bool)));
    connect(sync, SIGNAL(dataTransferProgress(qint64,qint64)), syncView, SLOT(transferProgress(qint64, qint64)));
    connect(sync, SIGNAL(downloadingFile(QString)), syncView, SLOT(updateFile(QString)));
    connect(sync, SIGNAL(finishedDownload()), syncView, SLOT(downloadFinished()));
    connect(syncView, SIGNAL(download()), sync, SLOT(requestDownload()));

    setCentralWidget(loginView);
    setWindowTitle("FTP Sync");
}

SyncWindow::~SyncWindow()
{
}

// Private Methods

// Private Slots

void SyncWindow::loginRequested(const QString &hostname, const QString &username, const QString &password)
{
    sync->setHostname(hostname);
    sync->setLocalPath(loginView->localPath());
    sync->requestLogin(username, password);
}

void SyncWindow::loginResult(bool ok)
{
    if (ok) {
        loginView->setEnabled(false);
        setCentralWidget(syncView);
        syncView->setUsername(sync->username());
    }

    else {
        loginView->enableLogin();
    }
}
