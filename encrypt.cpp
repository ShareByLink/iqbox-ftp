#include "encrypt.h"

const QString Encrypt::KEY = "udPIuSOiIIetNqAkCvgX";

Encrypt::Encrypt()
{
}

Encrypt::~Encrypt()
{
}


void Encrypt::encrypt(QString * const password)
{
    QByteArray encrypted;

    encrypted = password->toAscii();

    QChar key;
    foreach(key, KEY)
        encrypted = encrypt(key.toAscii(), encrypted.data(), encrypted.size());

    *password = QString(encrypted.toBase64());
}

void Encrypt::decrypt(QString * const password)
{
    QByteArray decrypted;

    decrypted = password->toAscii();
    decrypted = QByteArray::fromBase64(decrypted);

    QChar key;
    foreach(key, KEY)
        decrypted = encrypt(key.toAscii(), decrypted.data(), decrypted.size());

    *password = QString(decrypted);
}


QByteArray Encrypt::encrypt(char k, char *data, qint32 size)
{
    /*  Performs a XOR operation between every character of the password,
        passed in the data pointer, and a constant character 'KEY'. Note
        that this is the same operation for unecrypting, thanks to the
        nature of the XOR operation.
     */
    char * encoded;
    QByteArray encodedStr;
    encoded = new char[size];
    for (int i = 0; i < size; i++){
        encoded[i] = 0;
        encoded[i] = data[i] ^ k;
        encodedStr.append(encoded[i]);
    }
    return encodedStr;
}
