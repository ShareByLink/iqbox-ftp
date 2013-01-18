#include "syncwindow.h"

// Public Methods

SyncWindow::SyncWindow(QWidget *parent) :
    QMainWindow(parent)
{
    loginView = new SyncLogin;

    connect(loginView, SIGNAL(login(QString,QString,QString)), this, SLOT(loginRequested(QString,QString,QString)));

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
    sync = new SyncApp(hostname);
    sync->requestLogin(username, password);
}
