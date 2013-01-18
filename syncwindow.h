#ifndef SYNCWINDOW_H
#define SYNCWINDOW_H

#include <QMainWindow>

#include "global.h"
#include "synclogin.h"
#include "syncapp.h"

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

    // Private Methods


signals:
    
public slots:

private slots:

    void loginRequested(const QString & hostname, const QString & username, const QString & password);
    
};

#endif // SYNCWINDOW_H
