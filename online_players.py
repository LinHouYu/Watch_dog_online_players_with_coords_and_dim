from mcdreforged.api.all import *
import threading
import time
import re
import os
from datetime import datetime
from collections import defaultdict

PLUGIN_METADATA = {
    'id': 'Watch_dog_online_players_with_coords_and_dim',
    'version': '1.0.0',
    'name': 'Watch_dog_online_players_with_coords_and_dim',
    'author': 'LinHouyu',
    'link': 'https://github.com/LinHouYu',
    'description': '定时获取在线玩家及坐标、所在世界，写入独立日志文件'
}

INTERVAL = 5#刷新间隔秒
LOG_FILE = os.path.join(os.path.dirname(__file__), '日志.txt')#日志文件路径

online_players = []#当前在线玩家列表
player_state = defaultdict(lambda: {'pos': None, 'dim': None})#记录每个玩家的坐标和维度

DIM_TRANSLATE = {
    'overworld': '主世界',
    'the_nether': '地狱',
    'the_end': '末地',
}

def write_log(server, message: str):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] {message}"
    server.logger.info(f"[online_players_with_coords_and_dim_filelog] {line}")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(line + '\n')

def query_online_players(server):
    server.execute('list')#查询在线玩家

def query_player_coords_and_dim(server, player):
    server.execute(f'data get entity {player} Pos')#查坐标
    server.execute(f'data get entity {player} Dimension')#查维度

def loop(server):
    while True:
        query_online_players(server)
        time.sleep(INTERVAL)

def on_load(server, old):
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write("=== 玩家坐标与世界监控日志（中文世界名） ===\n")
    write_log(server, "插件已加载")
    threading.Thread(target=loop, args=(server,), daemon=True).start()

def on_info(server, info: Info):
    global online_players, player_state

    if not info.is_from_server:
        return

    if "players online" in info.content:
        parts = info.content.split(": ", 1)
        online_players = parts[1].split(", ") if len(parts) > 1 and parts[1] else []
        for p in online_players:
            query_player_coords_and_dim(server, p)
        return

    m = re.search(r'\b([0-9A-Za-z_]+)\s+has the following entity data:\s+(.*)$', info.content)
    if not m:
        return

    player = m.group(1)
    data = m.group(2).strip()

    pos_match = re.search(r'\[(-?\d+\.?\d*)d?,\s*(-?\d+\.?\d*)d?,\s*(-?\d+\.?\d*)d?\]', data)
    if pos_match:
        x, y, z = pos_match.groups()
        player_state[player]['pos'] = (x, y, z)

    dim_match = re.search(r'minecraft:([a-z_]+)', data)
    if dim_match:
        dim_id = dim_match.group(1)
        player_state[player]['dim'] = DIM_TRANSLATE.get(dim_id, dim_id)

    state = player_state[player]
    if state['pos'] and state['dim']:
        x, y, z = state['pos']
        write_log(server, f"{player} @ {x}, {y}, {z} - {state['dim']}")
        state['pos'] = None
