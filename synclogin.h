#ifndef SYNCLOGIN_H
#define SYNCLOGIN_H

#include <QWidget>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>

#include "global.h"

class SyncLogin : public QWidget
{
    Q_OBJECT

public:

    explicit SyncLogin(QWidget *parent = 0);

    ~SyncLogin();

    void enableLogin();

    QString localPath() const;
    
private:

    // Private Members

    QPushButton * browseButton;

    QLineEdit * hostEdit;

    QLabel * hostLabel;

    QPushButton * loginButton;

    QLineEdit * passwordEdit;

    QLabel * passwordLabel;

    QLineEdit * pathEdit;

    QLabel * pathLabel;

    QLineEdit * usernameEdit;

    QLabel * usernameLabel;

    // Private Methods

    void createLayouts();

    void createWidgets();

signals:

    void login(const QString & hostname, const QString & username, const QString & password);
    
public slots:

private slots:

    void browseForPath();

    void loginRequested();
};

#endif // SYNCLOGIN_H
