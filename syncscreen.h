#ifndef SYNCSCREEN_H
#define SYNCSCREEN_H

#include <QWidget>
#include <QLabel>
#include <QPushButton>

class SyncScreen : public QWidget
{
    Q_OBJECT

public:

    // Public Methods

    explicit SyncScreen(QWidget *parent = 0);

    ~SyncScreen();

private:

    // Private Members

    QLabel * fileLabel;

    QPushButton * downloadButton;

    QLabel * headLabel;

    QLabel * progressLabel;

    // Private Methods

    void createLayouts();

    void createWidgets();

signals:

    void download();
    
public slots:

    void downloadFinished();

    void setUsername(const QString & username);
    
    void transferProgress(qint64 done, qint64 total);

    void updateFile(const QString & file);

private slots:

    void downloadClicked();
};

#endif // SYNCSCREEN_H
