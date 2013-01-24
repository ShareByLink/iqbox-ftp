#ifndef ENCRYPT_H
#define ENCRYPT_H

#include <QString>

class Encrypt
{

    static const QString KEY;

    static QByteArray encrypt(char k, char *data, qint32 size);

public:

    Encrypt();

    ~Encrypt();

    static void encrypt(QString *const password);

    static void decrypt(QString *const password);


};
#endif // ENCRYPT_H
