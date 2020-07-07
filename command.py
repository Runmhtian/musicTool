from musicTool.MyFreeMp3 import Music
import re

pattern_ms_o = re.compile("ms\s+\-o\s(.+)")
pattern_ms_i = re.compile("ms\s+\-i(\d+)\s(.+)")
pattern_ms_a = re.compile("ms\s+\-a\s(.+)")
pattern_ms_n = re.compile("ms\s+\-n(\d+)\s(.+)")
pattern_set_dc = re.compile("set\s+dc\s+(.+)")
pattern_set_so = re.compile("set\s+so\s+(.+)")

help_message = """
ms -o [word]  仅搜索展示
ms -i1 [word]  搜索并下载第1个 n<=20
ms -a [word] 搜索并下载所有  尽量少用
ms -n20 [word] 搜索下载20个
set dc url_lrc url_320  设置默认下载歌词 下载高品质 [url_lrc,url_320,url_flac,url_128] 其中url_320，url_128 只能选一个
set so mg  设置查询源 咪咕(mg)  虾米(xm) 网易云(wy) 默认mg
quit 退出
"""


def search_o(music: Music, arg: tuple):
    items = music.search_music(arg[0])
    for item in items:
        print(item.index, item.title, item.author)


def search_a(music: Music, arg: tuple):
    music.search_and_download_all(arg[0])


def search_n(music: Music, arg: tuple):
    music.search_and_download_all(arg[1], max_num=int(arg[0]))


def search_i(music: Music, arg: tuple):
    music.search_and_download_index(arg[1], index=int(arg[0]))


def set_download_content(music: Music, arg: tuple):
    dc = arg[0]
    music.set_default_download_content(dc.split(' '))


def set_search_origin(music: Music, arg: tuple):
    so = arg[0]
    music.set_default_search_origin(so)


pattern_map = {
    pattern_ms_o: search_o,
    pattern_ms_a: search_a,
    pattern_ms_i: search_i,
    pattern_ms_n: search_n,
    pattern_set_dc: set_download_content,
    pattern_set_so: set_search_origin
}


def handle_command(cmd: str):
    cmd = cmd.strip()
    if cmd == '':
        return
    if cmd == 'man':
        print(help_message)
    if cmd == 'quit':
        m.close()
        import sys
        sys.exit()
    for pattern, method in pattern_map.items():
        t = pattern.match(cmd)
        if t:
            method(m, t.groups())
            break


m = Music()
while True:
    command = input(">>")
    try:
        handle_command(command)
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(command + " exec error")
