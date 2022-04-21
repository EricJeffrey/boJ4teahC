#!/usr/bin/python3
import asyncio
from datetime import datetime

CODE_WORKER_REG = 101
CODE_HELPER_REG = 102
CODE_DATA_SCR_SHOT = 201
CODE_DATA_CODE = 202

port = 8999

# { peername: (reader, writer), ... }
helpers = {}
workers = {}

helperLock = asyncio.Lock()
workerLock = asyncio.Lock()


def print_invalid():
    print("INVALID ReqCode")
    print("Valid reqCodes are: 101 102 for worker/helper register, 201 for worker screen shot, 202 for helper code data")


def send_one_packet(writer: asyncio.StreamWriter, code, data):
    def int2bytes(v):
        return v.to_bytes(4, 'little')
    length = len(data)
    header = int2bytes(code) + int2bytes(length) + int2bytes(0)
    writer.write(header)
    writer.write(data)


async def read_one_packet(reader: asyncio.StreamReader):
    def bytes2int(data: bytes):
        return int.from_bytes(data, 'big')
    reqCode = bytes2int(await reader.read(4))
    length = bytes2int(await reader.read(4))
    _ = await reader.read(4)
    data = None
    if length != 0:
        data = b''
        while len(data) < length:
            tmp = await reader.read(length - len(data))
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
    print("helper from {} connected".format(writer.get_extra_info("peername")))

    def addToHelper(peername):
        helpers[peername] = (reader, writer)

    def removeFromHelper():
        helpers.pop(peername)
        pass
    try:
        peername = ':'.join([str(v)
                             for v in writer.get_extra_info('peername')])
        await acquire_lock_then([helperLock], addToHelper, peername)
        while True:
            reqCode, data = await read_one_packet(reader)
            if reqCode == CODE_DATA_CODE:
                print("received code from helper {}".format(peername))
                await acquire_lock_then([workerLock, helperLock], sendCode, data)
            else:
                print_invalid()
    except ConnectionError:
        print("connection to helper {} closed".format(peername))
        await acquire_lock_then([helperLock], removeFromHelper)


async def handle_worker(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    print("worker from {} connected".format(writer.get_extra_info("peername")))

    def addToWorker(peername):
        workers[peername] = (reader, writer)

    def removeFromWorker():
        workers.pop(peername)

    try:
        peername = ':'.join([str(v)
                             for v in writer.get_extra_info('peername')])
        await acquire_lock_then([workerLock], addToWorker, peername)
        while True:
            reqCode, data = await read_one_packet(reader)
            if reqCode == CODE_DATA_SCR_SHOT:
                print("received screen from worker {}".format(peername))
                await acquire_lock_then([helperLock], sendScrShot, data)
            elif reqCode == CODE_DATA_CODE:
                print("received code from worker {}".format(peername))
                await acquire_lock_then([workerLock, helperLock], sendCode, data)
            else:
                print_invalid()
    except ConnectionError:
        print("connection to worker {} closed".format(peername))
        await acquire_lock_then([workerLock], removeFromWorker)


async def client_conn(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    reqCode, _ = await read_one_packet(reader)
    if reqCode == CODE_HELPER_REG:
        await handle_helper(reader, writer)
    elif reqCode == CODE_WORKER_REG:
        await handle_worker(reader, writer)
    else:
        print_invalid()


async def main():
    server = await asyncio.start_server(client_conn, "0.0.0.0", port)
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'cheater started on {addrs}')
    async with server:
        await server.serve_forever()


asyncio.run(main())
