from mcdreforged.api.all import *
import minecraft_data_api as mapi
import threading
import time
import csv
import os

INTERVAL = 5 #这里设置查询间隔，单位为秒
online_players = set()

DIM_TRANSLATE = {
    'overworld': '主世界',
    'the_nether': '地狱',
    'the_end': '末地',
}

def print_info(server, message: str):
    server.logger.info(f"[player_watchdog] {message}")

def log_to_csv(player: str, pos, dim_name: str, items: str):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    with open("玩家数据.csv", "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f).writerow([timestamp, player, dim_name, pos[0], pos[1], pos[2], items])

def init_csv():
    if not os.path.exists("玩家数据.csv"):
        with open("玩家数据.csv", "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f).writerow(["时间", "玩家", "维度", "X", "Y", "Z", "物品"])

def query_player_data(server, player: str):
    try:
        info = mapi.get_player_info(player)
        if not info:
            print_info(server, f"获取 {player} 数据失败")
            return

        pos = info.get('Pos')
        dim_id = info.get('Dimension', 'unknown').split(':')[-1]
        dim_name = DIM_TRANSLATE.get(dim_id, dim_id)

        items = []
        for item in info.get('Inventory', []):
            items.append(f"{item.get('id', 'unknown').split(':')[-1]}x{item.get('count', 1)}")
        for item in info.get('ArmorItems', []):
            iid = item.get('id', 'unknown').split(':')[-1]
            if iid != 'air':
                items.append(f"{iid}x{item.get('count', 1)}")
        for item in info.get('HandItems', []):
            iid = item.get('id', 'unknown').split(':')[-1]
            if iid != 'air':
                items.append(f"{iid}x{item.get('count', 1)}")
        for item in info.get('EnderItems', []):
            items.append(f"{item.get('id', 'unknown').split(':')[-1]}x{item.get('count', 1)}")

        items_str = ", ".join(items) if items else "空"

        if pos:
            log_to_csv(player, pos, dim_name, items_str)
            msg = f"{player} @ {pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f} - {dim_name} | 物品: {items_str}"
        else:
            msg = f"获取 {player} 坐标失败"

        print_info(server, msg)

    except Exception as e:
        print_info(server, f"获取 {player} 数据失败: {e}")

def loop(server):
    while True:
        for p in list(online_players):
            query_player_data(server, p)
        time.sleep(INTERVAL)

def on_load(server, old):
    print_info(server, "插件已加载（Minecraft Data API 版本）")
    init_csv()
    threading.Thread(target=loop, args=(server,), daemon=True).start()

def on_player_joined(server, player, info):
    online_players.add(player)
    print_info(server, f"{player} 上线")

def on_player_left(server, player):
    if player in online_players:
        online_players.remove(player)
    print_info(server, f"{player} 下线")
