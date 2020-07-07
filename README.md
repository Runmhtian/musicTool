## 简介
利用 selenium + requests 爬取 MyFreeMp3 来下载音乐

## 依赖
下载 http://npm.taobao.org/mirrors/chromedriver/84.0.4147.30/
pip install requests
pip install selenium
## 配置
config.ini 中配置
chrome_driver_path = "/Users/tianminghui/Downloads/chromedriver"
music_save_path = "/Users/tianminghui/Documents/music"

## 使用
python command.py

交互命令行
man 命令帮助
ms -o word 仅搜索展示
ms -i1 word  搜索并下载第1个 n<=20
ms -a word 搜索并下载所有  尽量少用
ms -n20 word 搜索下载20个
set dc url_lrc url_320  设置默认下载歌词 url_lrc,url_320,url_flac,url_128 其中url_320，url_128 只能选一个
set so mg  指出查询源 咪咕(mg)  虾米(xm) 网易云(wy) 默认mg
quit 退出