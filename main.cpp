#include <QApplication>

#include "syncwindow.h"

#include "encrypt.h"

int main(int argc, char** argv)
{
    QApplication syncApp(argc, argv);
    SyncWindow sync;

    sync.show();
    return syncApp.exec();
}
