#if !defined(EVENT_HANDLER_CPP)
#define EVENT_HANDLER_CPP

#include "EventHandler.h"
#include "Response.h"
#include <chrono>

set<int> EventHandler::workerSockets;
set<int> EventHandler::helperSockets;
set<int> EventHandler::clientSockets;

queue<vector<char>> EventHandler::codeQueue;
queue<vector<char>> EventHandler::screenShotQueue;

mutex EventHandler::codeScrQMutex;

condition_variable EventHandler::codeScrQCondVar;

void EventHandler::writerJob() {
    loggerInstance()->info("Writer thread started");
    while (true) {
        try {
            std::unique_lock<mutex> lock(codeScrQMutex);
            codeScrQCondVar.wait(lock,
                                 [] { return !codeQueue.empty() || !screenShotQueue.empty(); });
            while (!codeQueue.empty() && !clientSockets.empty()) {
                vector<char> data = codeQueue.front();
                codeQueue.pop();
                vector<char> respData = Response::wrapRespData(ReqCode::CODE_DATA, data);
                for (auto &&clientSd : clientSockets) {
                    writen(clientSd, respData.data(), respData.size());
                }
                loggerInstance()->info({"CodeData ------------> All Clients"});
            }
            while (!screenShotQueue.empty() && !helperSockets.empty()) {
                vector<char> data = screenShotQueue.front();
                screenShotQueue.pop();
                loggerInstance()->debug({"screen shot data fetched"});
                for (auto &&clientSd : helperSockets) {
                    // write
                    vector<char> respData = Response::wrapRespData(ReqCode::SCREEN_SHOT_DATA, data);
                    writen(clientSd, respData.data(), respData.size());
                }
                loggerInstance()->info({"ScreenShot ------------> Helper"});
            }
        } catch (const std::exception &e) {
            loggerInstance()->error({"writer throw an exception:", e.what()});
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
        loggerInstance()->info({"connection from", parseAddr(tmpRet.first), "established"});
    }
}

void EventHandler::handleReadEv(int sd, PtrPoller pollerPtr) {
    loggerInstance()->debug("handling read event");
    try {
        Request request = readRequest(sd);
        // do job according to request.Code
        switch (request.getReqCode()) {
            case ReqCode::REG_HELPER:
                helperSockets.insert(sd);
                loggerInstance()->info("REG ------------ Helper");
                break;
            case ReqCode::REG_WORKER:
                workerSockets.insert(sd);
                loggerInstance()->info("REG ------------ Worker");
                break;
            case ReqCode::CODE_DATA:
                // put into msg
                putCode(request.getData());
                loggerInstance()->info("CodeData <------------");
                break;
            case ReqCode::SCREEN_SHOT_DATA:
                // put into msg
                putScrShot(request.getData());
                loggerInstance()->info("ScreenShot <------------");
                loggerInstance()->debug("screen shot data put into queue");
                break;
            default:
                break;
        }
    } catch (const std::exception &e) {
        loggerInstance()->error(string("read client request failed: ") + e.what());
        removeSock(sd, pollerPtr);
    }
}

int EventHandler::handleErrEv(int sd, int listenSd, PtrPoller pollerPtr) {
    if (sd == listenSd) {
        close(listenSd);
        loggerInstance()->error("EPOLLERR on listensd, closed and exit");
        throw runtime_error("unexpected EPOLLERR on listensd");
    } else {
        loggerInstance()->error({"EPOLLERR on socket:", to_string(sd)});
        removeSock(sd, pollerPtr);
    }
    return 0;
}

void EventHandler::removeSock(int sd, PtrPoller pollerPtr) {
    pollerPtr->epollDelete(sd);
    clientSockets.erase(sd);
    workerSockets.erase(sd);
    helperSockets.erase(sd);
    close(sd);
}

void EventHandler::handleHupEv(int sd, PtrPoller pollerPtr) {
    removeSock(sd, pollerPtr);
    loggerInstance()->info("EPOLLRDHUP, Client closed");
}

void EventHandler::putCode(const vector<char> &data) {
    std::lock_guard<mutex> guard(codeScrQMutex);
    codeQueue.push(data);
    codeScrQCondVar.notify_one();
}
void EventHandler::putScrShot(const vector<char> &data) {
    std::lock_guard<mutex> guard(codeScrQMutex);
    screenShotQueue.push(data);
    codeScrQCondVar.notify_one();
}
Request readRequest(int sd) {
    char headerBytes[REQ_HEADER_LEN + 1] = {};
    int ret = read(sd, headerBytes, REQ_HEADER_LEN);
    if (ret == -1) {
        loggerInstance()->sysError(errno, "call to read failed");
        throw runtime_error("call to read failed");
    }
    if (!Request::isReqCodeValid(Request::parseReqCode(headerBytes))) {
        loggerInstance()->error("Invalid request code");
        throw runtime_error("invalid request code");
    }
    const int bodyLen = Request::parseBodyLen(headerBytes);
    vector<char> body(bodyLen);
    if (bodyLen > 0)
        ret = readn(sd, body.data(), bodyLen);
    return Request::buildFromBytes(headerBytes, body);
}

#endif // EVENT_HANDLER_CPP
