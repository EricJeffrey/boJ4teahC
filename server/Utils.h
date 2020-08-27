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

#endif // UTILS_H
