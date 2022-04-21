#if !defined(RESPONSE_H)
#define RESPONSE_H

#include "Logger.h"
#include "Request.h"
#include <arpa/inet.h>
#include <vector>

using std::vector;

class Response {
private:
public:
    Response() {}
    ~Response() {}

    static vector<char> wrapRespData(int respCode, vector<char> &data) {
        vector<char> res(REQ_HEADER_LEN + data.size());
        auto toNbytes = [&res](int x, int startPos) {
            x = htonl(x);
            for (int i = 0; i < 4; i++)
                res[startPos + (3 - i)] = (x >> (i * 8));
        };
        toNbytes(respCode, 0);
        toNbytes(data.size(), 4);
        toNbytes(0, 8);
        std::copy(data.begin(), data.end(), res.begin() + REQ_HEADER_LEN);
        return res;
    }
};

#endif // RESPONSE_H
