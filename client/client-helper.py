""" helper客户端代码 """

from datetime import datetime
import ctypes
from socket import ntohl, socket, AF_INET, SOCK_STREAM
from sys import path_hooks
from threading import Condition, Thread, Lock
from tkinter import *
from tkinter import font
from tkinter.ttk import *
from queue import Queue
import win32clipboard

CODE_REG_WORKER = 101
CODE_REG_HELPER = 102
CODE_SCRSHOT_DATA = 201
CODE_CODE_DATA = 202


# scrShotDirPath = "./scrShot"
scrShotIndex = 1
host = "192.168.31.14"
port = 8000
byteorder = "big"

stop = False

writerCodeQueue = Queue()
writerCodeQLock = Lock()
writerCodeQCondVar = Condition(writerCodeQLock)

codeTextArea = None
listbox = None


def strLogWithTime(info):
    now = datetime.now()
    return "%s   %s" % (str(now)[0:19], info)
    pass


def copy2clipboard(data: str):
    """ 将data中的数据拷贝到剪贴板上 """
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(data)
    win32clipboard.CloseClipboard()
    pass


def sendData(sock: socket, reqCode, length=2, data=b'ok'):
    def toBytes(n): return n.to_bytes(4, byteorder=byteorder)
    sock.sendall(toBytes(reqCode) + toBytes(length) + toBytes(0) + data)


def readerJob(sock: socket):
    while True:
        try:
            headers = sock.recv(12)
            reqCode = int.from_bytes(headers[0:4], byteorder="little")
            bodyLen = int.from_bytes(headers[4:8], byteorder="little")
            print("header got, code: %d, len: %d" % (reqCode, bodyLen))
            # addi = int.from_bytes(headers[8:12], byteorder=byteorder)
            if reqCode == 0:
                print("invalid reqCode 0, close & exit")
                sock.close()
                exit(-1)
            body = bytes()
            while len(body) < bodyLen:
                body += sock.recv(bodyLen - len(body))
            if reqCode == CODE_CODE_DATA:
                bodyStr = str(body, encoding="utf-8")
                copy2clipboard(bodyStr)
                listbox.insert(1, strLogWithTime("收到了的别人的代码，放到剪贴板了"))
            elif reqCode == CODE_SCRSHOT_DATA:
                ret = onScrShotGot(body)
                listbox.insert(1, strLogWithTime(
                    "收到了别人发的截图，保存为%d.png了" % (ret)))
            else:
                pass
        except Exception as e:
            print("connection closed, reader thread exit: %s" % (e))
            return -1


def writerJob(sock: socket):
    while not stop:
        writerCodeQLock.acquire()
        writerCodeQCondVar.wait()
        if stop:
            break
        while not writerCodeQueue.empty():
            # send here
            data = writerCodeQueue.get()
            data = data.encode("utf-8")
            # print(data)
            sendData(sock, 202, len(data), data)
        writerCodeQLock.release()


def onScrShotGot(scrShotData: bytes):
    global scrShotIndex
    ret = -1
    with open("./" + str(scrShotIndex) + ".png", mode="wb") as fp:
        ret = scrShotIndex
        fp.write(scrShotData)
        scrShotIndex += 1
    return ret


def addDataToQueu():
    data = codeTextArea.get('1.0', 'end')
    writerCodeQLock.acquire()
    writerCodeQueue.put(data)
    writerCodeQCondVar.notify()
    writerCodeQLock.release()


def startGUI(onUICreated):
    global codeTextArea, listbox
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    # 获取屏幕的缩放因子
    ScaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
    # 设置程序缩放
    window = Tk()
    window.tk.call('tk', 'scaling', ScaleFactor/75)
    window.title("Helper")
    window.config(background="#f5f5f5")
    maxW, maxH = window.maxsize()
    window.state('zoomed')
    # window.geometry("%dx%d" % (maxW, maxH))
    # window.geometry('1280x720')

    codeTextArea = Text(window, font=('等线', 14), height=20, width=60)
    codeTAW, codeTAH = maxW * 2 / 3, maxH * 6 / 8
    codeTextArea.place(x=10, y=10, width=codeTAW, height=codeTAH)
    scrollbar = Scrollbar(window)
    scrollbar.place(x=codeTAW+10, y=10, height=codeTAH, width=20)
    scrollbar.config(command=codeTextArea.yview)
    codeTextArea.config(yscrollcommand=scrollbar.set)

    btn = Button(window, text='发送', command=addDataToQueu)
    btn.place(x=10, y=10 + codeTAH + 20, width=codeTAW, height=60)

    listbox = Listbox(window)
    listbox.place(x=codeTAW + 40, y=10, width=maxW /
                  3 - 50, height=maxH * 7 / 8)
    listbox.insert(0, "这里会显示所有消息")

    onUICreated()
    window.mainloop()
    pass


def connect():
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))
    sendData(sock, CODE_REG_HELPER)
    return sock


def exitNotify():
    writerCodeQLock.acquire()
    writerCodeQCondVar.notify_all()
    writerCodeQLock.release()
    pass


def work():
    try:
        global stop
        sock = connect()
        t1 = Thread(target=readerJob, args=(sock,))
        t2 = Thread(target=writerJob, args=(sock,))
        def startAllThread(): t1.start(); t2.start()
        startGUI(onUICreated=startAllThread)
        stop = True
        sock.close()
    except Exception as e:
        print(e)
    exitNotify()
    pass


if __name__ == "__main__":
    work()
