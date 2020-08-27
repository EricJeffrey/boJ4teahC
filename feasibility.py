
""" 验证可行性 """

from os import getpid, getppid, system
from socket import AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from threading import Thread
import socket
import tkinter
from keyboard import add_hotkey
import win32clipboard  # works on win only
from PIL import ImageGrab
from tkinter import *
from tkinter.ttk import *
import ctypes
from io import BytesIO


def getScreenShot():
    """ 获取屏幕截图 """
    im = ImageGrab.grab()
    imgByteArray = BytesIO()
    im.save(imgByteArray, "PNG")
    imgBytes = imgByteArray.getvalue()  # bytes
    im.save("./foo.png")
    pass


def copy2clipboard(data: str):
    """ 将data中的数据拷贝到剪贴板上 """
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(data)
    win32clipboard.CloseClipboard()
    pass


def serverWork():
    # create socket
    port = 2333
    listenSd = socket.socket(AF_INET, SOCK_STREAM)
    listenSd.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    listenSd.bind(("0.0.0.0", port))
    listenSd.listen(5)
    print("server started on port %d" % (port))
    threadList = []
    while True:
        (childSd, addr) = listenSd.accept()
        childThread = Thread(target=handleChildConn, args=(childSd, addr))
        threadList.append(childThread)
        childThread.start()
    pass


def lisetnKeyboard(callback):
    """ 监听键盘热键 """
    hotkey = "ctrl+alt+f2"
    add_hotkey(hotkey=hotkey, callback=callback)
    pass


def writeIdToFile():
    fp = open("./foo.txt", mode="w", encoding="utf-8")
    fp.write(str(getpid()))
    fp.write("\n")
    fp.write(str(getppid()))
    fp.write("\n")
    pass


def guiFeasibility():
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
    # 获取屏幕的缩放因子
    ScaleFactor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
    # 设置程序缩放
    window = Tk()
    window.tk.call('tk', 'scaling', ScaleFactor/75)
    window.title("Helper")
    window.geometry('1280x720')
    l = Label(window, text="", font=('Consolas', 14), width=50)
    l.pack()
    tv = Text(window, font=('等线', 14), height=20, width=60)
    tv.pack()
    l = Label(window, text="", font=('Consolas', 14), width=100)
    l.pack()
    btn = Button(window, text='粘贴', width=80)
    btn.pack()
    window.mainloop()
    pass


if __name__ == "__main__":

    # serverWork()
    # lisetnKeyboard(callback=getScreenShot)
    # s = input()
    # copy2clipboard(s)
    # while True:
    #     pass
    guiFeasibility()
    pass
