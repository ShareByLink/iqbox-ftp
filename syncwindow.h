#ifndef SYNCWINDOW_H
#define SYNCWINDOW_H

#include <QMainWindow>
#include <QSystemTrayIcon>

#include "global.h"
#include "synclogin.h"
#include "syncapp.h"
#include "syncscreen.h"

class SyncWindow : public QMainWindow
{
    Q_OBJECT

public:

    // Public Methods

    explicit SyncWindow(QWidget *parent = 0);

    ~SyncWindow();

private:

    // Private Members

    SyncLogin * loginView;

    SyncApp * sync;

    QSystemTrayIcon * syncIcon;

    SyncScreen * syncView;

    // Private Methods

signals:
    
public slots:

private slots:

    void loginRequested(const QString & hostname, const QString & username, const QString & password);

    void loginResult(bool ok);
};

#endif // SYNCWINDOW_H
