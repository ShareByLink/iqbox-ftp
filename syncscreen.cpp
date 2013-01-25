#include <QVBoxLayout>

#include "syncscreen.h"

// Public Methods

SyncScreen::SyncScreen(QWidget *parent) :
    QWidget(parent)
{
    setFixedSize(600, 380);
    createWidgets();
    createLayouts();

    connect(downloadButton, SIGNAL(clicked()), this, SLOT(downloadClicked()));
}

SyncScreen::~SyncScreen()
{
}

// Private Methods

void SyncScreen::createLayouts()
{
    QVBoxLayout * mainLayout = new QVBoxLayout;
    QHBoxLayout * downloadLayout = new QHBoxLayout;

    downloadLayout->addWidget(fileLabel, 90, Qt::AlignLeft);
    downloadLayout->addWidget(progressLabel, 10, Qt::AlignRight);

    mainLayout->addWidget(headLabel, 25);
    mainLayout->addWidget(downloadButton, 25, Qt::AlignLeft);
    mainLayout->addStretch(50);
    mainLayout->addLayout(downloadLayout);

    setLayout(mainLayout);
}

void SyncScreen::createWidgets()
{
    QFont labelFont("", 15);
    QFont buttonFont("", -1, 500);

    headLabel = new QLabel(this);
    headLabel->setFont(labelFont);
    headLabel->setText("Welcome <strong>%1</strong>. <br>Click 'Download' to start syncing");

    downloadButton = new QPushButton(this);
    downloadButton->setFont(buttonFont);
    downloadButton->setText("Download");
    downloadButton->setFixedWidth(width() / 4);

    fileLabel = new QLabel(this);
    progressLabel = new QLabel(this);
}

// Public Slots

void SyncScreen::downloadFinished()
{
    progressLabel->clear();
    fileLabel->clear();
    downloadButton->setEnabled(true);
}

void SyncScreen::setUsername(const QString &username)
{
    headLabel->setText(headLabel->text().arg(username));
}

void SyncScreen::transferProgress(qint64 done, qint64 total)
{
    // Preventing division by zero.
    total = total == 0 ? 1 : total;
    qint64 percent = done * 100 / total;

    progressLabel->setText(QString::number(percent) + "%");
}

void SyncScreen::updateFile(const QString &file)
{
    fileLabel->setText(file);
}

// Private Slots

void SyncScreen::downloadClicked()
{
    downloadButton->setEnabled(false);

    emit download();
}
