#if !defined(REQUEST_H)
#define REQUEST_H

#include "Logger.h"
#include <arpa/inet.h>
#include <errno.h>
#include <stdexcept>
#include <cstring>
#include <exception>
#include <unistd.h>
#include <vector>

using std::runtime_error;
using std::vector;

enum ReqCode {
    HEART_BEAT = 100,
    CODE_DATA = 202,
    SCREEN_SHOT_DATA = 201,
    REG_WORKER = 101,
    REG_HELPER = 102
};

static const size_t REQ_HEADER_LEN = 4 * 3;

class Request {
private:
    int requestCode, bodyLen, addition;
    vector<char> data;

public:
    Request() {}
    ~Request() {}

    static Request buildFromBytes(char *headers, vector<char> &body) {
        Request res;
        res.requestCode = ntohl(*reinterpret_cast<int *>(headers));
        res.bodyLen = ntohl(*reinterpret_cast<int *>(headers + 4));
        res.addition = ntohl(*reinterpret_cast<int *>(headers + 8));
        res.data = std::move(body);
        return res;
    }

    vector<char> &getData() { return data; }
    int getReqCode() { return requestCode; }

    static int parseBodyLen(char *rawHeaders) {
        const int bodyLen = *(reinterpret_cast<int *>(rawHeaders + 4));
        return ntohl(bodyLen);
    }
};

#endif // REQUEST_H
