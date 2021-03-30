
#include "Utils.h"
#include "Poller.h"
#include "Request.h"
#include "EventHandler.h"
#include <algorithm>

void writerJob() {}

int work() {
    try {
        const int port = 8000;
        int listenSd = createServerSocket(port, "0.0.0.0");
        PtrPoller pollerPtr = std::make_shared<Poller>(listenSd);
        thread(EventHandler::writerJob).detach();

        loggerInstance()->info({"Server started on port:", to_string(port)});
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
        loggerInstance()->error({"server start failed:", e.what()});
        exit(-1);
    }
    return 0;
}

void config() {
    using std::cerr;
    bool runAsDaemon = false;
    bool out2stderr = true;
    bool debugOn = false;
    const string logOutPath = "/data/boJ4teahC/log.txt";

    cerr << "config:" << endl;
    cerr << "\tdaemon: " << (runAsDaemon ? "true" : "false") << endl;
    cerr << "\tlogout: " << ((!runAsDaemon) && out2stderr ? "stderr" : logOutPath) << endl;
    cerr << "\tdebug: " << (debugOn ? "true" : "false") << endl;

    if (runAsDaemon) {
        if (daemon(1, 1) == -1) {
            perror("daemon failed:");
            exit(-1);
        }
    }
    if (!runAsDaemon && out2stderr)
        Logger::init(std::cerr);
    else
        Logger::init(logOutPath);
    loggerInstance()->setDebug(debugOn);
}

int main(int argc, char const *argv[]) {
    config();
    work();
    return 0;
}
