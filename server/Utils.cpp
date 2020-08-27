#if !defined(UTILS_CPP)
#define UTILS_CPP

#include "Utils.h"
#include <sstream>

using std::runtime_error;

// Create a traditional server socket listen on host:port
// Throw on Error
int createServerSocket(int port, const string &host) {
    int sd;
    sd = socket(AF_INET, SOCK_STREAM, 0);
    if (sd == -1) {
        loggerInstance()->sysError(errno, "call to socket failed");
        throw runtime_error("call to socket failed");
    }
    int opt = 1;
    if (setsockopt(sd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(int)) == -1) {
        loggerInstance()->sysError(errno, "setsockopt failed");
        throw runtime_error("call to setsockopt failed");
    }
    sockaddr_in addr;
    addr.sin_family = AF_INET, addr.sin_port = htons(port);
    inet_aton(host.c_str(), &addr.sin_addr);
    if (bind(sd, (sockaddr *)&addr, sizeof(addr)) == -1) {
        loggerInstance()->sysError(errno, "bind failed");
        throw runtime_error("call to bind failed");
    }
    if (listen(sd, 1024) == -1) {
        loggerInstance()->sysError(errno, "listen failed");
        throw runtime_error("call to listen failed");
    }
    return sd;
}

typedef std::pair<sockaddr_in, int> SockAddr2Int;

// Call accept(), return <{}, -1> on error, -2 on EINTR
SockAddr2Int acceptConn(int listenSd) {
    using std::make_pair;
    sockaddr_in addr;
    socklen_t addrLen;
    int ret = accept(listenSd, (sockaddr *)&addr, &addrLen);
    if (ret == -1) {
        const int tmpErrno = errno;
        if (tmpErrno == EINTR) {
            loggerInstance()->sysError(tmpErrno, "call to accept interrupted by signal");
            return make_pair(addr, -2);
        }
        loggerInstance()->sysError(errno, "call to accept failed");
        return make_pair(addr, -1);
    }
    return make_pair(addr, ret);
}

string vecChar2Str(const vector<char> &data) {
    std::stringstream ss;
    for (auto &&c : data)
        ss << c;
    return ss.str();
}

#endif // UTILS_CPP
