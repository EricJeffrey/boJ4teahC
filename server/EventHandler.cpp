#if !defined(EVENT_HANDLER_CPP)
#define EVENT_HANDLER_CPP

#include <chrono>
#include "Response.h"
#include "EventHandler.h"

vector<int> EventHandler::workerSockets;
vector<int> EventHandler::helperSockets;
set<int> EventHandler::clientSockets;

queue<vector<char>> EventHandler::codeQueue;
queue<vector<char>> EventHandler::screenShotQueue;

mutex EventHandler::codeQMutex;
mutex EventHandler::scrShotQeMutex;

condition_variable EventHandler::codeQCondVar;
condition_variable EventHandler::scrShotQCondVar;

void EventHandler::writerJob() {
    loggerInstance()->info("writer job started");
    while (true) {
        const auto waitTime = std::chrono::milliseconds(10);
        {
            std::unique_lock<mutex> lock(codeQMutex);
            codeQCondVar.wait_for(lock, waitTime, [] { return !codeQueue.empty(); });
            while (!codeQueue.empty()) {
                vector<char> data = codeQueue.front();
                codeQueue.pop();
                vector<char> respData = Response::wrapRespData(ReqCode::CODE_DATA, data);
                loggerInstance()->debug({"code data fetched:", vecChar2Str(respData)});
                for (auto &&clientSd : clientSockets) {
                    int ret = write(clientSd, respData.data(), respData.size());
                    if (ret == -1) {
                        loggerInstance()->sysError(errno, "write failed");
                        throw runtime_error("call to write failed");
                    }
                }
                loggerInstance()->debug({"code data send to client"});
            }
        }
        {
            std::unique_lock<mutex> lock(scrShotQeMutex);
            scrShotQCondVar.wait_for(lock, waitTime, [] { return !screenShotQueue.empty(); });
            while (!screenShotQueue.empty()) {
                vector<char> data = screenShotQueue.front();
                screenShotQueue.pop();
                loggerInstance()->debug({"screen shot data fetched"});
                for (auto &&clientSd : helperSockets) {
                    // write
                    vector<char> respData = Response::wrapRespData(ReqCode::SCREEN_SHOT_DATA, data);
                    int ret = write(clientSd, respData.data(), respData.size());
                    if (ret == -1) {
                        loggerInstance()->sysError(errno, "write failed");
                        throw runtime_error("call to write failed");
                    }
                    loggerInstance()->debug({"screen shot data send to client"});
                }
            }
        }
    }
}

void EventHandler::handleAcceptEv(int listenSd, PtrPoller poller) {
    loggerInstance()->debug("handling new conn");
    SockAddr2Int tmpRet = acceptConn(listenSd);
    if (tmpRet.second == -1) {
        loggerInstance()->error("call to acceptConn failed");
        throw runtime_error("call to acceptConn failed");
    } else if (tmpRet.second == -2) {
        loggerInstance()->warn("call to acceptConn interrupted");
    } else {
        poller->epollAdd(tmpRet.second, EPOLLIN | EPOLLRDHUP | EPOLLHUP);
        clientSockets.insert(tmpRet.second);
        loggerInstance()->debug("new connection add to poller");
    }
}

void EventHandler::handleReadEv(int sd, PtrPoller poller) {
    loggerInstance()->debug("handling read event");
    Request request = readRequest(sd);
    // loggerInstance()->debug({"request got, body:", vecChar2Str(request.getData())});
    // do job according to request.Code
    switch (request.getReqCode()) {
        case ReqCode::REG_HELPER:
            helperSockets.push_back(sd);
            break;
        case ReqCode::REG_WORKER:
            workerSockets.push_back(sd);
            break;
        case ReqCode::CODE_DATA:
            // put into msg
            putCode(request.getData());
            break;
        case ReqCode::SCREEN_SHOT_DATA:
            // put into msg
            putScrShot(request.getData());
            break;
        default:
            break;
    }
}

int EventHandler::handleErrEv(int sd, int listenSd, PtrPoller pollerPtr) {
    loggerInstance()->error({"EPOLLERR on socket:", to_string(sd)});
    if (sd == listenSd) {
        close(listenSd);
        loggerInstance()->info("epoll error on listensd, closed and exit");
        throw runtime_error("unexpected EPOLLERR on listensd");
    } else {
        pollerPtr->epollDelete(sd);
        clientSockets.erase(sd);
        close(sd);
    }
    return 0;
}

void EventHandler::handleHupEv(int sd, PtrPoller pollerPtr) {
    pollerPtr->epollDelete(sd);
    clientSockets.erase(sd);
    loggerInstance()->info("EPOLLRDHUP got, client closed");
}

void EventHandler::putCode(const vector<char> &data) {
    std::lock_guard<mutex> guard(codeQMutex);
    codeQueue.push(data);
}
void EventHandler::putScrShot(const vector<char> &data) {
    std::lock_guard<mutex> guard(scrShotQeMutex);
    screenShotQueue.push(data);
}
Request readRequest(int sd) {
    char headerBytes[REQ_HEADER_LEN + 1] = {};
    int ret = read(sd, headerBytes, REQ_HEADER_LEN);
    if (ret == -1) {
        loggerInstance()->sysError(errno, "call to read failed");
        throw runtime_error("call to read failed");
    }
    const int bodyLen = Request::parseBodyLen(headerBytes);
    vector<char> body(bodyLen);
    if (bodyLen > 0) {
        ret = read(sd, body.data(), bodyLen);
        if (ret == -1) {
            loggerInstance()->sysError(errno, "call to read failed");
            throw runtime_error("call to read failed");
        }
    }
    return Request::buildFromBytes(headerBytes, body);
}

#endif // EVENT_HANDLER_CPP
