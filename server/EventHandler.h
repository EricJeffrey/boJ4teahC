#if !defined(EVENT_HANDLER_H)
#define EVENT_HANDLER_H

#include "Logger.h"
#include "Utils.h"
#include "Request.h"
#include "Poller.h"
#include <queue>
#include <condition_variable>

using std::condition_variable;
using std::queue;

class EventHandler {
public:
    static set<int> workerSockets;
    static set<int> helperSockets;
    static set<int> clientSockets;

    static queue<vector<char>> codeQueue;
    static queue<vector<char>> screenShotQueue;

    static mutex codeScrQMutex;
    static condition_variable codeScrQCondVar;

    static void handleAcceptEv(int listenSd, PtrPoller poller);
    static void handleReadEv(int sd, PtrPoller poller);
    static int handleErrEv(int sd, int listenSd, PtrPoller pollerPtr);
    static void handleHupEv(int sd, PtrPoller pollerPtr);

    static void writerJob();

    static void putCode(const vector<char> &data);
    static void putScrShot(const vector<char> &data);
};
Request readRequest(int sd);

#endif // EVENT_HANDLER_H
