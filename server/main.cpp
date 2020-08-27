
#include "Utils.h"
#include "Poller.h"
#include "Request.h"
#include "EventHandler.h"
#include <algorithm>

void writerJob() {}

void work() {
    try {
        const int port = 8000;
        int listenSd = createServerSocket(port, "0.0.0.0");
        PtrPoller pollerPtr = std::make_shared<Poller>(listenSd);
        thread(EventHandler::writerJob).detach();

        loggerInstance()->debug({"server started on port: ", to_string(port)});
        while (true) {
            EpollEvs2IntRet tmpWaitRet = pollerPtr->epollWait();
            if (tmpWaitRet.second == -1) {
                pollerPtr->closePoller();
                throw runtime_error("call to epollWait failed");
            } else if (tmpWaitRet.second == -2) {
                loggerInstance()->warn("poller interrupted by signal, ignoring");
                continue;
            }
            for (auto &&ev : tmpWaitRet.first) {
                if (ev.events & (EPOLLRDHUP | EPOLLHUP)) {
                    EventHandler::handleHupEv(ev.data.fd, pollerPtr);
                } else if (ev.events & EPOLLERR) {
                    EventHandler::handleErrEv(ev.data.fd, listenSd, pollerPtr);
                } else if (ev.data.fd == listenSd) {
                    EventHandler::handleAcceptEv(listenSd, pollerPtr);
                } else {
                    EventHandler::handleReadEv(ev.data.fd, pollerPtr);
                }
            }
        }
    } catch (const std::exception &e) {
        loggerInstance()->error("server start failed");
    }
}

int main(int argc, char const *argv[]) {
    Logger::init(std::cerr);
    loggerInstance()->setDebug(true);
    work();
    return 0;
}
