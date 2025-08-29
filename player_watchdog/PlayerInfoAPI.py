# -*- coding: utf-8 -*-
import copy
import re
import ast
import json
from threading import Lock

try:
    import Queue
except ImportError:
    import queue as Queue


work_queue = {}
queue_lock = Lock()
query_count = 0


def convertMinecraftJson(text):
    r"""
    Convert Minecraft json string into standard json string and json.loads() it
    Also if the input has a prefix of "xxx has the following entity data: " it will automatically remove it, more ease!
    Example available inputs:
    - Alex has the following entity data: {a: 0b, big: 2.99E7, c: "minecraft:white_wool", d: '{"text":"rua"}'}
    - {a: 0b, big: 2.99E7, c: "minecraft:white_wool", d: '{"text":"rua"}'}
    - [0.0d, 10, 1.7E9]
    - {Air: 300s, Text: "\\o/..\""}
    - "hello"
    - 0b
    """
    text = re.sub(r'^.* has the following entity data: ', '', text)
    text = re.sub(r'(?<=\d)[a-zA-Z](?=(\D|$))', '', text)
    text = re.sub(r'([a-zA-Z.]+)(?=:)', '"\g<1>"', text)

    list_a = re.split(r'""[a-zA-Z.]+":', text)
    list_b = re.findall(r'""[a-zA-Z.]+":', text)
    result = list_a[0]
    for i in range(len(list_b)):
        result += list_b[i].replace('""', '"').replace('":', ':') + list_a[i + 1]

    text = ''.join([i for i in mcSingleQuotationJsonReader(result)])
    return json.loads(text)


def mcSingleQuotationJsonReader(data):
    part = data
    count = 1
    while True:
        spliter = part.split(r"'{", 1)
        yield spliter[0]
        if len(spliter) == 1:
            return
        else:
            part_2 = spliter[1].split(r"}'")
            index = 0
            res = jsonCheck("".join(part_2[:index + 1]))
            while not res:
                index += 1
                if index == len(part_2):
                    raise RuntimeError("Out of index")
                res = jsonCheck("".join(part_2[:index + 1]))
            j_dict = ""
            while res:
                j_dict = res
                index += 1
                if index == len(part_2):
                    break
                res = jsonCheck("".join(part_2[:index + 1]))

            yield j_dict

        part_2 = part_2[index:]
        part = part_2[0]
        if len(part_2) > 1:
            for i in part_2[1:]:
                part += "}'"
                part += i
        count += 1


def jsonCheck(j):
    checking = "".join(["{", j, "}"])
    try:
        checking = checking.replace(r'\\', "\\")
        res = json.loads(checking)
    except ValueError:
        try:
            res = ast.literal_eval(checking)
        except:
            return False
    data = json.dumps({"data": json.dumps(res)})
    return data[9:-1]


def get_queue(player):
    with queue_lock:
        if player not in work_queue:
            work_queue[player] = Queue.Queue()
    return work_queue[player]


def clean_queue():
    global work_queue, queue_lock
    with queue_lock:
        for q in work_queue.values():
            q.queue.clear()


def getPlayerInfo(server, player, path='', timeout=5):
    if len(path) >= 1 and not path.startswith(' '):
        path = ' ' + path
    command = 'data get entity {}{}'.format(player, path)
    if hasattr(server, 'MCDR') and server.is_rcon_running():
        result = server.rcon_query(command)
    else:
        global query_count
        query_count += 1
        try:
            server.execute(command)
            result = get_queue(player).get(timeout=timeout)
        except Queue.Empty:
            return None
        finally:
            query_count -= 1
    try:
        return convertMinecraftJson(result)
    except json.JSONDecodeError:
        server.logger.error('Fail to parse Minecraft json {}'.format(result))
        return None


def onServerInfo(server, info):
    global work_queue
    if info.isPlayer == 0 and re.match(r'^\w+ has the following entity data: .*$', info.content):
        player = info.content.split(' ')[0]
        if query_count > 0:
            get_queue(player).put(info.content)
        else:
            clean_queue()


def on_info(server, info):
    info2 = copy.copy(info)
    info2.isPlayer = info2.is_player
    onServerInfo(server, info2)


if __name__ == '__main__':
    for line in convertMinecraftJson.__doc__.splitlines():
        if re.match(r'^\s*- .*$', line):
            s = line.split('-')[-1]
            print('{} -> {}'.format(s, convertMinecraftJson(s)))
