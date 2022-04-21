#if !defined(UTILS_H)
#define UTILS_H

#include "Logger.h"
#include <stdexcept>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <vector>

using std::runtime_error;
using std::vector;

// Create a traditional server socket listen on host:port
// Throw on Error
int createServerSocket(int port, const string &host);

typedef std::pair<sockaddr_in, int> SockAddr2Int;

// Call accept(), return <{}, -1> on error, -2 on EINTR
SockAddr2Int acceptConn(int listenSd);

string vecChar2Str(const vector<char> &);

int writen(int sd, const char *buf, ssize_t numToWrite);
int readn(int sd, char *buf, ssize_t numToRead);

string parseAddr(sockaddr_in addr);

#endif // UTILS_H
