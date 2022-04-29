#!/usr/bin/python3
import asyncio
from datetime import datetime
import json

CODE_WORKER_REG = 101
CODE_HELPER_REG = 102
CODE_DATA_SCR_SHOT = 201
CODE_DATA_CODE = 202


def dothex2num(x):
    return sum([int(v) * (256 ** (3 - i)) for i, v in enumerate(x.split('.'))])


# 只允许教育网的IP访问
# [ ["59.192.0.0", "59.255.255.255", 4194304], ... ]
allowed_ip = []
with open("./allowed_ip.json") as fp:
    allowed_ip = json.load(fp)
    allowed_ip = [ips.split('/') for ips in allowed_ip]
    allowed_ip = [[dothex2num(ips[0]), 32 - int(ips[1])] for ips in allowed_ip]
    allowed_ip = [[ips[0], ips[0] + 2 ** ips[1] - 1] for ips in allowed_ip]


def is_ip_allowed(ip):
    ipn = dothex2num(ip)
    for v in allowed_ip:
        if ipn >= v[0] and ipn <= v[1]:
            return True
    return False


port = 8999

# { peername: (reader, writer), ... }
helpers = {}
workers = {}

helperLock = asyncio.Lock()
workerLock = asyncio.Lock()


def print_flush(s):
    print(s, flush=True)


def print_invalid():
    print_flush("INVALID ReqCode")
    # print_flush(
    #     "Valid reqCodes are: 101 102 for worker/helper register, 201 for worker screen shot, 202 for helper code data")


def print_debug(s):
    print("DEBUG {}".format(s), flush=True)


def send_one_packet(writer: asyncio.StreamWriter, code, data):
    def int2bytes(v):
        return v.to_bytes(4, 'little')
    length = len(data)
    header = int2bytes(code) + int2bytes(length) + int2bytes(0)
    writer.write(header)
    writer.write(data)


async def read_one_packet(reader: asyncio.StreamReader):
    async def read_with_timeout(reader: asyncio.StreamReader, nbytes, timeout=1):
        return await asyncio.wait_for(reader.read(nbytes), timeout)

    def bytes2int(data: bytes):
        return int.from_bytes(data, 'big')
    tmp = await read_with_timeout(reader, 4)
    reqCode = bytes2int(tmp)
    length = bytes2int(await read_with_timeout(reader, 4))
    _ = await read_with_timeout(reader, 4)
    data = None
    if length != 0:
        data = b''
        while len(data) < length:
            tmp = await read_with_timeout(reader, length)
            data += tmp
    return (reqCode, data)


async def acquire_lock_then(locks, cb, data=None):
    for lock in locks:
        await lock.acquire()
    if data is not None:
        cb(data)
    else:
        cb()
    for lock in locks:
        lock.release()


def sendCode(data):
    ts = str(datetime.now().timestamp())
    with open("./tmp.code"+ts+".txt", mode='wt') as fp:
        fp.write(data.decode(encoding='utf-8'))
    for _, w in workers.values():
        send_one_packet(w, CODE_DATA_CODE, data)
    for _, w in helpers.values():
        send_one_packet(w, CODE_DATA_CODE, data)


def sendScrShot(data):
    ts = str(datetime.now().timestamp())
    with open("./tmp.img"+ts+".jpg", mode='wb') as fp:
        fp.write(data)
    for _, w in helpers.values():
        send_one_packet(w, CODE_DATA_SCR_SHOT, data)


async def handle_helper(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    print_flush("helper from {} connected".format(
        writer.get_extra_info("peername")))

    def addToHelper(peername): helpers[peername] = (reader, writer)
    def removeFromHelper(): helpers.pop(peername)
    try:
        peername = ':'.join([str(v)
                             for v in writer.get_extra_info('peername')])
        await acquire_lock_then([helperLock], addToHelper, peername)
        while True:
            try:
                reqCode, data = await read_one_packet(reader)
                if reqCode == CODE_DATA_CODE:
                    print_flush(
                        "received code from helper {}".format(peername))
                    await acquire_lock_then([workerLock, helperLock], sendCode, data)
                else:
                    print_invalid()
                    return
            except asyncio.exceptions.TimeoutError:
                pass
    except Exception:
        print_flush("connection to helper {} closed".format(peername))
        if workerLock.locked():
            workerLock.release()
        await acquire_lock_then([helperLock], removeFromHelper)


async def handle_worker(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    print_flush("worker from {} connected".format(
        writer.get_extra_info("peername")))

    def addToWorker(peername):
        workers[peername] = (reader, writer)

    def removeFromWorker():
        workers.pop(peername)

    try:
        peername = ':'.join([str(v)
                             for v in writer.get_extra_info('peername')])
        await acquire_lock_then([workerLock], addToWorker, peername)
        while True:
            try:
                reqCode, data = await read_one_packet(reader)
                if reqCode == CODE_DATA_SCR_SHOT:
                    print_flush(
                        "received screen from worker {}".format(peername))
                    await acquire_lock_then([helperLock], sendScrShot, data)
                elif reqCode == CODE_DATA_CODE:
                    print_flush(
                        "received code from worker {}".format(peername))
                    await acquire_lock_then([workerLock, helperLock], sendCode, data)
                else:
                    print_invalid()
                    return
            except asyncio.exceptions.TimeoutError:
                pass
    except Exception:
        print_flush("connection to worker {} closed".format(peername))
        if helperLock.locked():
            helperLock.release()
        await acquire_lock_then([workerLock], removeFromWorker)


async def client_conn(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info('peername')
    peerIP = peer[0]
    if is_ip_allowed(peerIP):
        try:
            reqCode, _ = await read_one_packet(reader)
            if reqCode == CODE_HELPER_REG:
                await handle_helper(reader, writer)
            elif reqCode == CODE_WORKER_REG:
                await handle_worker(reader, writer)
            else:
                print_invalid()
        except asyncio.exceptions.TimeoutError:
            print_flush("client {} register timeout".format(peerIP))
    else:
        print_flush("IP not allowed: {}".format(peerIP))


async def main():
    server = await asyncio.start_server(client_conn, "0.0.0.0", port)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print_flush(f'cheater started on {addrs}')
    async with server:
        await server.serve_forever()

asyncio.run(main())
