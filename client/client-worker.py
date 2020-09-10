from datetime import datetime
import ctypes
from io import BytesIO
from socket import ntohl, socket, AF_INET, SOCK_STREAM
from threading import Condition, Thread, Lock
from queue import Queue
from PIL import ImageGrab
import win32clipboard
from keyboard import add_hotkey

imgIndex = 1

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


def logout(info):
    now = datetime.now()
    print("%s   %s" % (str(now)[0:19], info))


def copy2clipboard(data: str):
    """ 将data中的数据拷贝到剪贴板上 """
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(data)
    win32clipboard.CloseClipboard()
    pass


def getScreenShot():
    """ 获取屏幕截图 """
    im = ImageGrab.grab()
    imgByteArray = BytesIO()
    im.save(imgByteArray, "PNG")
    try:
        global imgIndex
        with open("./%d.png" % (imgIndex), mode="wb") as fp:
            fp.write(imgByteArray.getvalue())
        imgIndex += 1
    except Exception as e:
        print("截图保存失败: ", e)
    return imgByteArray.getvalue()  # bytes


def getFromClipboard():
    txt = ""
    try:
        win32clipboard.OpenClipboard()
        txt = win32clipboard.GetClipboardData()
        win32clipboard.CloseClipboard()
    except Exception as e:
        print("获取剪贴板数据出错: %s" % (e))
    return txt


def onHotkeyPress(key):
    # print("onHotKeyPress, key: %s" % (key))
    if key == HOT_KEY_GET_CLIP_DATA:
        codeData = getFromClipboard().encode(encoding="utf-8")
        if len(codeData) == 0:
            print("剪贴板无数据")
        else:
            queueMutex.acquire()
            codeQueue.put(codeData)
            queueCond.notify()
            queueMutex.release()
            logout("剪贴板内容已发送")
    elif key == HOT_KEY_GET_SCR_SHOT:
        scrShotData = getScreenShot()
        queueMutex.acquire()
        scrShotQueue.put(scrShotData)
        queueCond.notify()
        queueMutex.release()
        logout("屏幕截图已发送")
    pass


def sendData(sock: socket, reqCode, length=2, data=b'ok'):
    def toBytes(n): return n.to_bytes(4, byteorder=byteorder)
    sock.sendall(toBytes(reqCode) + toBytes(length) + toBytes(0) + data)


def connect():
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))
    sendData(sock, CODE_REG_WORKER)
    return sock


def readerJob4Worker(sock: socket):
    """ 读取服务端代码数据 """
    while not stop:
        try:
            headers = sock.recv(12)
            reqCode = ntohl(int.from_bytes(headers[0:4], byteorder=byteorder))
            bodyLen = ntohl(int.from_bytes(headers[4:8], byteorder=byteorder))
            if reqCode == 0:
                print("响应码为0，连接已断开")
                return
            print("收到数据, 数据代号: %d, 长度: %d" % (reqCode, bodyLen))
            # addi = int.from_bytes(headers[8:12], byteorder=byteorder)
            body = bytes()
            while len(body) < bodyLen:
                body += sock.recv(bodyLen - len(body))
            if reqCode == CODE_CODE_DATA:
                bodyStr = str(body, encoding="utf-8")
                copy2clipboard(bodyStr)
                logout("收到了别人的代码，添加到剪贴板了")
        except UnicodeEncodeError as e:
            print("编码错误 %s" % (e))
        except Exception as e:
            print("连接已断开 %s" % (e))
            return -1
    pass


def writerJob4Worker(sock: socket):
    """ 读取队列数据发送到服务端 """
    while not stop:
        queueMutex.acquire()
        queueCond.wait_for(lambda: (not codeQueue.empty())
                           or (not scrShotQueue.empty()) or (stop))
        if stop:
            return
        while not codeQueue.empty():
            codeData = codeQueue.get()
            sendData(sock, CODE_CODE_DATA, len(codeData), codeData)
        while not scrShotQueue.empty():
            scrShotData = scrShotQueue.get()
            print("截图大小: %dKB" % (len(scrShotData) / 1024))
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
        add_hotkey(hotkey=HOT_KEY_GET_SCR_SHOT,
                   callback=onHotkeyPress, args=(HOT_KEY_GET_SCR_SHOT, ))
        add_hotkey(hotkey=HOT_KEY_GET_CLIP_DATA,
                   callback=onHotkeyPress, args=(HOT_KEY_GET_CLIP_DATA, ))
        Thread(target=writerJob4Worker, args=(sock, )).start()
        print("已连接到服务器\nCtrl+Alt+F2 -- 获取截图并发送\nCtrl+Alt+F3 -- 发送剪贴板内容\nCtrl+Pause -- 退出")
        readerJob4Worker(sock)
    except Exception as e:
        print("Error: %s" % (e))
    else:
        sock.close()
        exitAndNotify()


if __name__ == "__main__":
    work()
