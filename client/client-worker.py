from datetime import datetime
import ctypes
from io import BytesIO
from socket import ntohl, socket, AF_INET, SOCK_STREAM
from sys import path_hooks
from threading import Condition, Thread, Lock
from queue import Queue
from PIL import ImageGrab
import win32clipboard
from keyboard import add_hotkey

host = "192.168.31.14"
port = 8000
byteorder = "big"

stop = False

CODE_REG_WORKER = 101
CODE_REG_HELPER = 102
CODE_SCRSHOT_DATA = 201
CODE_CODE_DATA = 202

HOT_KEY_GET_SCR_SHOT = "ctrl+alt+f2"
HOT_KEY_GET_CLIP_DATA = "ctrl+alt+f3"

codeQueue = Queue()
scrShotQueue = Queue()
queueMutex = Lock()
queueCond = Condition(queueMutex)

clipboardMutex = Lock()

def logout(info):
    now = datetime.now()
    print("%s   %s" % (str(now)[0:19], info))


def copy2clipboard(data: str):
    """ 将data中的数据拷贝到剪贴板上 """
    clipboardMutex.acquire()
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(data)
    win32clipboard.CloseClipboard()
    clipboardMutex.release()
    pass


def getScreenShot():
    """ 获取屏幕截图 """
    im = ImageGrab.grab()
    imgByteArray = BytesIO()
    im.save(imgByteArray, "PNG")
    return imgByteArray.getvalue()  # bytes


def getFromClipboard():
    clipboardMutex.acquire()
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    txt = win32clipboard.GetClipboardData()
    win32clipboard.CloseClipboard()
    clipboardMutex.release()
    return txt


def onHotkeyPress(key):
    print("onHotKeyPress, key: %s" % (key))
    if key == HOT_KEY_GET_CLIP_DATA:
        codeData = getFromClipboard().encode(encoding="utf-8")
        queueMutex.acquire()
        codeQueue.put(codeData)
        queueCond.notify()
        queueMutex.release()
    elif key == HOT_KEY_GET_SCR_SHOT:
        scrShotData = getScreenShot()
        queueMutex.acquire()
        codeQueue.put(scrShotData)
        queueCond.notify()
        queueMutex.release()
    pass


def sendData(sock: socket, reqCode, length=2, data=b'ok'):
    def toBytes(n): return n.to_bytes(4, byteorder=byteorder)
    sock.sendall(toBytes(reqCode) + toBytes(length) + toBytes(0) + data)


def connect():
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))
    sendData(sock, CODE_REG_HELPER)
    return sock


def readerJob4Worker(sock: socket):
    """ 读取服务端代码数据 """
    while not stop:
        try:
            headers = sock.recv(12)
            reqCode = int.from_bytes(headers[0:4], byteorder="little")
            bodyLen = int.from_bytes(headers[4:8], byteorder="little")
            if reqCode == 0:
                print("响应码为0，连接已断开")
                return
            print("header got, code: %d, len: %d" % (reqCode, bodyLen))
            # addi = int.from_bytes(headers[8:12], byteorder=byteorder)
            body = sock.recv(bodyLen)
            print("body got")
            if reqCode == CODE_CODE_DATA:
                bodyStr = str(body, encoding="utf-8")
                copy2clipboard(bodyStr)
                logout("收到了别人的代码，添加到剪贴板了")
            else:
                pass
        except Exception as e:
            print("connection closed, reader thread exit: %s" % (e))
            return -1
    pass


def writerJob4Worker(sock: socket):
    """ 读取队列数据发送到服务端 """
    while not stop:
        queueMutex.acquire()
        queueCond.wait()
        if stop:
            return
        while not codeQueue.empty():
            codeData = codeQueue.get()
            sendData(sock, CODE_CODE_DATA, len(codeData), codeData)
        while not scrShotQueue.empty():
            scrShotData = scrShotQueue.get()
            sendData(sock, CODE_SCRSHOT_DATA, len(scrShotData), scrShotData)
        queueMutex.release()


def exitAndNotify():
    global stop
    stop = True
    queueMutex.acquire()
    queueCond.notify_all()
    queueMutex.release()


def work():
    try:
        sock = connect()
        sendData(sock, CODE_REG_WORKER)
        add_hotkey(hotkey=HOT_KEY_GET_SCR_SHOT,
                   callback=onHotkeyPress, args=(HOT_KEY_GET_SCR_SHOT, ))
        add_hotkey(hotkey=HOT_KEY_GET_CLIP_DATA,
                   callback=onHotkeyPress, args=(HOT_KEY_GET_CLIP_DATA, ))
        Thread(target=writerJob4Worker, args=(sock, ))
        readerJob4Worker(sock)
    except Exception as e:
        print("Error: %s" % (e))
    else:
        sock.close()
        exitAndNotify()



if __name__ == "__main__":
    work()
