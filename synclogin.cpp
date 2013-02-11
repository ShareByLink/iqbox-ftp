#include <QHBoxLayout>
#include <QVBoxLayout>
#include <QFileDialog>
#include <QDesktopServices>

#include "synclogin.h"
#include "encrypt.h"

// Public Methods

SyncLogin::SyncLogin(QWidget *parent) :
    QWidget(parent)
{
    setFixedSize(300, 380);
    createWidgets();
    createLayouts();
}

SyncLogin::~SyncLogin()
{
}

void SyncLogin::enableLogin()
{
    loginButton->setEnabled(true);
}


QString SyncLogin::localPath() const
{
    return pathEdit->text();
}

// Private Methods

void SyncLogin::createLayouts()
{
    QHBoxLayout * mainLayout = new QHBoxLayout;
    QVBoxLayout * widgetsLayout = new QVBoxLayout;

    widgetsLayout->addStretch(50);
    widgetsLayout->addWidget(usernameLabel);
    widgetsLayout->addWidget(usernameEdit);
    widgetsLayout->addWidget(passwordLabel);
    widgetsLayout->addWidget(passwordEdit);
    widgetsLayout->addWidget(hostLabel);
    widgetsLayout->addWidget(hostEdit);
    widgetsLayout->addStretch(50);
    widgetsLayout->addWidget(pathLabel);
    widgetsLayout->addWidget(pathEdit);
    widgetsLayout->addWidget(browseButton, 40, Qt::AlignRight);
    widgetsLayout->addStretch(30);
    widgetsLayout->addWidget(loginButton);
    widgetsLayout->addStretch(80);

    mainLayout->addStretch(30);
    mainLayout->addLayout(widgetsLayout, 30);
    mainLayout->addStretch(30);

    setLayout(mainLayout);
}

void SyncLogin::createWidgets()
{
    QSize widgetsSize(210, 30);
    QFont labelsFont("", 11, 500);

    // Checking for previoulsy used settings.
    QSettings settings(AppSettings::companyName, AppSettings::appName);
    QString defaultLocation = QDesktopServices::storageLocation(QDesktopServices::DocumentsLocation);
    QString decryptedPass = settings.value(AppSettings::keyPassword).toString();

    defaultLocation.append(QDir::separator() + AppSettings::appName + QDir::separator());
    Encrypt::decrypt(&decryptedPass);

    QString username = !settings.value(AppSettings::keyUsername).toString().isEmpty() ?
                settings.value(AppSettings::keyUsername).toString() : "";

    QString password = !settings.value(AppSettings::keyPassword).toString().isEmpty() ?
                decryptedPass : "";

    QString hostname = !settings.value(AppSettings::keyHostname).toString().isEmpty() ?
                settings.value(AppSettings::keyHostname).toString() : "";

    QString localPath = !settings.value(AppSettings::keyLocalPath).toString().isEmpty() ?
                settings.value(AppSettings::keyLocalPath).toString() :
                defaultLocation;

    usernameLabel = new QLabel(this);
    usernameLabel->setText("Username");
    usernameLabel->setFont(labelsFont);

    usernameEdit = new QLineEdit(this);
    usernameEdit->setFixedSize(widgetsSize);
    usernameEdit->setText(username);

    passwordLabel = new QLabel(this);
    passwordLabel->setText("Password");
    passwordLabel->setFont(labelsFont);

    passwordEdit = new QLineEdit(this);
    passwordEdit->setFixedSize(widgetsSize);
    passwordEdit->setEchoMode(QLineEdit::Password);
    passwordEdit->setText(password);

    hostLabel = new QLabel(this);
    hostLabel->setText("Host");
    hostLabel->setFont(labelsFont);

    hostEdit = new QLineEdit(this);
    hostEdit->setFixedSize(widgetsSize);
    hostEdit->setText(hostname);

    pathLabel = new QLabel(this);
    pathLabel->setText("Local path");
    pathLabel->setFont(labelsFont);

    pathEdit = new QLineEdit(this);
    pathEdit->setFixedSize(widgetsSize);
    pathEdit->setReadOnly(true);
    pathEdit->setText(localPath);

    browseButton = new QPushButton(this);
    browseButton->setText("Browse");
    connect(browseButton, SIGNAL(clicked()), this, SLOT(browseForPath()));

    loginButton = new QPushButton(this);
    loginButton->setText("Login");
    loginButton->setFont(labelsFont);
    connect(loginButton, SIGNAL(clicked()), this, SLOT(loginRequested()));
}

// Public Slots

// Private Slots

void SyncLogin::browseForPath()
{
    QString localPath = QFileDialog::getExistingDirectory(this, "Select a folder");
    pathEdit->setText(localPath);
    pathEdit->setCursorPosition(0);
}

void SyncLogin::loginRequested()
{
    QString host = hostEdit->text();
    QString path = pathEdit->text();

    if (!host.isEmpty() && !path.isEmpty()) {
        loginButton->setEnabled(false);
        emit login(host, usernameEdit->text(), passwordEdit->text());

        // Always saves last used input.
        QSettings settings(AppSettings::companyName, AppSettings::appName);
        QString encryptedPass = passwordEdit->text();
        Encrypt::encrypt(&encryptedPass);

        settings.setValue(AppSettings::keyUsername, usernameEdit->text());
        settings.setValue(AppSettings::keyPassword, encryptedPass);
        settings.setValue(AppSettings::keyHostname, hostEdit->text());
        settings.setValue(AppSettings::keyLocalPath, pathEdit->text());
    }
}
