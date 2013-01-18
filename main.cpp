#include <QApplication>

#include "syncwindow.h"

int main(int argc, char** argv)
{
    QApplication syncApp(argc, argv);
    SyncWindow sync;

    sync.show();
    syncApp.exec();
}
