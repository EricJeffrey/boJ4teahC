#!/usr/bin/python3
from socket import AF_INET, SOCK_STREAM, socket
from time import sleep
import win32clipboard

byteorder = "big"

tmpCode = b'''using std::runtime_error;
using std::vector;
enum ReqCode {
    HEART_BEAT = 100,
    CODE_DATA = 202,
    SCREEN_SHOT_DATA = 201,
    REG_WORKER = 101,
    REG_HELPER = 102
};
'''


def sendData(sock: socket, reqCode, len, data):
    def toBytes(n): return n.to_bytes(4, byteorder=byteorder)
    sock.send(toBytes(reqCode) + toBytes(len) + toBytes(0) + data)


def copy2clipboard(data: str):
    """ 将data中的数据拷贝到剪贴板上 """
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardText(data)
    win32clipboard.CloseClipboard()
    pass


if __name__ == "__main__":
    host = "192.168.31.14"
    port = 8000
    sock = socket(AF_INET, SOCK_STREAM)
    sock.connect((host, port))
    while True:
        s = input("1: 读数据, 2: 发数据, 0: 退出 --> ")
        s = int(s)
        if s == 1:
            resBytes = sock.recv(1024)
            copy2clipboard(str(resBytes[12::], encoding='utf-8'))
            print("数据已复制到剪贴板")
            pass
        elif s == 2:
            data = input("输入要发送到服务器的内容 --> ")
            data = data.encode(encoding="utf-8")
            sendData(sock, 202, len(data), data)
            print("数据已发送到服务器")
            pass
        else:
            break
    sock.close()
    pass
