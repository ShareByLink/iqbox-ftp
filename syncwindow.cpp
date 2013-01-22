#include "syncwindow.h"

// Public Methods

SyncWindow::SyncWindow(QWidget *parent) :
    QMainWindow(parent)
{
    loginView = new SyncLogin;
    sync = new SyncApp;

    connect(loginView, SIGNAL(login(QString,QString,QString)), this, SLOT(loginRequested(QString,QString,QString)));
    connect(sync, SIGNAL(loggedIn(bool)), this, SLOT(loginResult(bool)));

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
    }

    else {
        loginView->enableLogin();
    }
}
