"""
http://tool.liumingye.cn/music/

"""
import collections
import time
import logging
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains

import requests
import os
from configparser import ConfigParser

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s')

# http://npm.taobao.org/mirrors/chromedriver/84.0.4147.30/

conf = ConfigParser()
conf.read("config.ini")
chrome_driver_path = conf["musicTool"]["chrome_driver_path"]
music_save_path = conf["musicTool"]["music_save_path"]

MusicItem = collections.namedtuple("MusicItem", ["index", "title", "author", "download_elem", "time_elem"])
MusicInfo = collections.namedtuple("MusicInfo", ["name", "url_128", "url_320", "url_lrc", "url_flac"])


def http_response_valid(resp, success_status):
    if success_status == resp.status_code:
        logging.info("http url:{%s} success" % resp.request.url)
        return True
    logging.error("http url:{%s} error:status_code:%d" % (resp.request.url, resp.status_code))
    logging.error(resp.text)
    return False


class SearchOrigin:
    MI_GU = "mg"
    XIA_MI = "xm"
    WANG_YI = "wy"

    _search_origin = {
        MI_GU: "migu",
        XIA_MI: "xiami",
        WANG_YI: "YQD",
    }

    @staticmethod
    def contain(t: str):
        return t in SearchOrigin._search_origin.keys()

    @staticmethod
    def get_value(key: str):
        return SearchOrigin._search_origin.get(key)


class UrlType:
    URL_128 = 'url_128'  # 标准
    URL_320 = 'url_320'  # 高品
    URL_FLAC = 'url_flac'  # 无损
    URL_LRC = 'url_lrc'  # 歌词
    _all_set = {URL_128, URL_320, URL_FLAC, URL_LRC}

    @staticmethod
    def contain(dc: str):
        return dc in UrlType._all_set


class check_load_success:
    """
    判断是否下一页加载完成
    """

    def __init__(self, page_size, page_num):
        self.__page_size = page_size
        self.__page_num = page_num

    def __call__(self, driver: WebDriver):
        start = self.__page_size * (self.__page_num - 1)
        elems = driver.find_elements_by_class_name("init")
        if elems and len(elems) > start:
            return True
        return False


class Music:
    URL_APP_ONENINE_CC = "app.onenine.cc"

    def __init__(self):
        logging.info("开始初始化 Music")
        # 配置chrome浏览器(无头模式)
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")
        # chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument("--mute-audio")  # 静音
        self.driver = webdriver.Chrome(chrome_driver_path, options=chrome_options)
        self.driver.get("http://tool.liumingye.cn/music/?page=searchPage")
        self.__sess = requests.session()
        self.__sess.headers[
            "User-Agent"] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36"
        self.__page_num = 0
        self.__current_search_word = ''
        self.__page_size = 20
        self.__default_download_content = [UrlType.URL_LRC, UrlType.URL_320]
        # find_element 时的等待时间
        self.__default_implicitly_wait_time = 10
        self.driver.implicitly_wait(self.__default_implicitly_wait_time)
        self.default_search_origin = SearchOrigin.MI_GU
        logging.info("musicTool 初始化结束")

    def search_music(self, search_word: str, search_option=None):
        """
        查询 返回 [MusicItem]
        :param search_word:str
        :param search_option:str
        :return:list
        """
        logging.info("查询关键词为:%s" % search_word)
        if not self._is_search_page():
            self.driver.get("http://tool.liumingye.cn/music/?page=searchPage")

        if not search_option:
            search_option = self.default_search_origin
        # 搜索类型
        elem = self._find_element('type')
        Select(elem).select_by_value(SearchOrigin.get_value(search_option))
        # 搜索文本
        elem = self._find_element('input')
        elem.clear()
        elem.send_keys(search_word)
        elem.send_keys(Keys.RETURN)

        self.__page_num = 1
        self.__current_search_word = search_word
        return self._search_page_parse()

    def _search_page_parse(self):
        """
        解析查询结果页
        :return:list
        """
        logging.info("开始解析查询结果:%s" % self.__current_search_word)
        result = []
        elems = self._find_elements("init", find_type=By.CLASS_NAME)
        if not elems:
            logging.warning("没有找到搜索结果,%s" % self.__current_search_word)
            return result
        start = self.__page_size * (self.__page_num - 1)
        end = self.__page_size * self.__page_num
        if len(elems) <= start:
            logging.error("page size error,elems size[%d],start[%d]" % (len(elems), start))
            return
        # 先关闭隐式等待 否则没有time_elem 会等待很久
        self.driver.implicitly_wait(0)
        for elem in elems[start:end]:
            index = elem.find_element_by_class_name("aplayer-list-index").text
            title = elem.find_element_by_class_name("aplayer-list-title").text
            author = elem.find_element_by_class_name("aplayer-list-author").text
            download_elem = elem.find_element_by_css_selector("[class='aplayer-list-download iconfont icon-xiazai']")
            time_elem = None
            try:
                # wy 包含aplayer-list-time
                time_elem = elem.find_element_by_class_name("aplayer-list-time")
            except NoSuchElementException:
                pass
            result.append(MusicItem(index, title, author, download_elem, time_elem))
        self.driver.implicitly_wait(self.__default_implicitly_wait_time)
        return result

    def _load_next_page(self):
        """
        加载下一页  返回 [MusicItem]
        :return:list
        """
        self.__page_num = self.__page_num + 1
        logging.info("开始加载第%d页" % self.__page_num)
        elem = self._find_element("aplayer-more", By.CLASS_NAME)
        if elem:
            elem.click()
            # 隐式等待 在这里不好使，他是增加了 init 元素，find 能够找到
            WebDriverWait(self.driver, 10, 1).until(check_load_success(self.__page_size, self.__page_num))
            return self._search_page_parse()
        logging.warning("没有下一页了")
        return []

    def _scroll_download(self, index: int, elem: WebElement):
        # 当index为10倍数的时候 滚动到底部  不然出现点击到别的组件上
        if index % 10 == 0:
            self._scroll_bottom()

        # 当 index % 20 = 1 时 也就是说 加载了下一页时 滚动第一个到顶部
        if index % 20 == 1:
            self._scroll_to_elem(elem)
            self._scroll_distance(-50)

    def _parse_download(self, item: MusicItem):
        """
        解析要下载的音乐
        :param item:MusicItem
        :return:MusicInfo
        """
        logging.info("开始解析[%s]下载链接" % item.title)
        download_elem = item.download_elem
        self._scroll_download(int(item.index), download_elem)
        time_elem = item.time_elem
        # 若有有time_elem 则需要鼠标移动过去 并点击
        if time_elem:
            actions = ActionChains(self.driver)
            actions.move_to_element(time_elem)
            actions.click(download_elem)
            actions.perform()
        else:
            download_elem.click()

        elem = self._find_element("name")
        if not elem:
            logging.error("parse download elem error")
            return
        name = elem.get_attribute("value")
        elem = self._find_element(UrlType.URL_128)
        url_128 = elem.get_attribute("value") if elem else None

        elem = self._find_element(UrlType.URL_320)
        url_320 = elem.get_attribute("value") if elem else None

        elem = self._find_element(UrlType.URL_LRC)
        url_lrc = elem.get_attribute("value") if elem else None

        elem = self._find_element(UrlType.URL_FLAC)
        url_flac = elem.get_attribute("value") if elem else None
        return MusicInfo(name, url_128, url_320, url_lrc, url_flac)

    def _download_music(self, music_info: MusicInfo, url_type=UrlType.URL_320):
        """
        下载指定类型音乐
        app.onenine.cc  直接下载
        218.205.239.34  ip的需要跳转
        :param music_info: MusicInfo
        :param url_type: str
        :return:
        """
        logging.info("开始下载 %s,%s" % (music_info.name, url_type))
        url = getattr(music_info, url_type)
        save_path = Music.get_save_path(url_type, music_info.name)
        logging.info("保存路径为,%s" % save_path)
        if Music.URL_APP_ONENINE_CC in url:
            resp = self.__sess.get(url)
            if http_response_valid(resp, 200):
                with open(save_path, 'wb') as f:
                    for data in resp.iter_content(chunk_size=1024):
                        f.write(data)
        else:
            resp = self.__sess.get(url, allow_redirects=False)
            if http_response_valid(resp, 302):
                location = resp.headers["Location"]
                resp = self.__sess.get(location)
                if http_response_valid(resp, 200):
                    with open(save_path, 'wb') as f:
                        for data in resp.iter_content(chunk_size=1024):
                            f.write(data)

    def _scroll_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def _download_close(self):
        elem = self._find_element("[class='btn btn-primary']", By.CSS_SELECTOR)
        if elem:
            elem.click()

    @staticmethod
    def get_save_path(url_type, name):
        suffix = '.mp3'
        if url_type == UrlType.URL_FLAC:
            suffix = '.flac'
        if url_type == UrlType.URL_LRC:
            suffix = '.lrc'
        return os.path.join(music_save_path, name + suffix)

    def _find_element(self, element, find_type=By.ID):
        try:
            return self.driver.find_element(find_type, element)
        except NoSuchElementException:
            logging.warning("NoSuchElementException in driver:%s" % element)
            return None

    def _find_elements(self, element, find_type='id'):
        try:
            return self.driver.find_elements(find_type, element)
        except NoSuchElementException:
            logging.warning("NoSuchElementException in driver:%s" % element)
            return None

    def _is_search_page(self):
        if "搜索 - MYFREEMP3" in self.driver.title:
            return True
        return False

    def download(self, item: MusicItem, download_content=None):
        """
        默认下载 高品质 + 歌词
        :param item:
        :param download_content:
        :return:
        """
        if download_content is None:
            download_content = self.__default_download_content
        music_info = self._parse_download(item)
        for url_type in download_content:
            self._download_music(music_info, url_type)
        self._download_close()

    def search_and_download_all(self, search_world, max_num=-1, download_content=None,
                                search_option=None):
        """
        下载搜索出来的所有
        :param search_world: str
        :param max_num: int
        :param download_content: list
        :param search_option: str
        :return:
        """
        count = 0
        item_list = self.search_music(search_world, search_option)
        item_list.reverse()
        if item_list:
            while len(item_list) > 0:
                item = item_list.pop()
                self.download(item, download_content)
                count += 1
                if max_num != -1 and count >= max_num:
                    return
                if len(item_list) == 0:
                    l = self._load_next_page()
                    if len(l) == 0:
                        break
                    l.reverse()
                    item_list.extend(l)

    def search_and_download_index(self, search_world, download_content=None, index=1, search_option=None):
        """
        下载第index个
        :param search_world:
        :param download_content:
        :param index:
        :param search_option:
        :return:
        """
        item_list = self.search_music(search_world, search_option)
        if item_list and len(item_list) > 0 and index <= len(item_list):
            self.download(item_list[index - 1], download_content)

    def _focus(self, elem: WebElement):
        """
        貌似不好使
        :param elem:
        :return:
        """
        self.driver.execute_script("arguments[0].focus();", elem)

    def _scroll_to_elem(self, elem: WebElement, top=True):
        """
        不管是 true 还是 false  都被页面 顶部和尾部遮挡
        :param elem:
        :param top:
        :return:
        """
        if top:
            self.driver.execute_script("arguments[0].scrollIntoView();", elem)
        else:
            self.driver.execute_script("arguments[0].scrollIntoView(false);", elem)

    def _scroll_distance(self, dis: int):
        self.driver.execute_script("window.scrollBy(0,%s);" % dis)

    def set_default_download_content(self, download_content: list):
        if not download_content or len(download_content) == 0:
            logging.error("download_content error")
            return
        for dc in download_content:
            if not UrlType.contain(dc):
                logging.error("download_content error:%s" % dc)
        self.__default_download_content = download_content
        logging.info("set default_download_content:%s" % download_content)

    def set_default_search_origin(self, search_origin: str):
        if SearchOrigin.contain(search_origin):
            self.default_search_origin = search_origin
            logging.info("set default_search_origin:%s" % search_origin)
        else:
            logging.error("search_origin error")

    def test(self):
        self.search_music("毛不易")
        self.search_music("周杰伦")

    def close(self):
        time.sleep(2)
        self.driver.quit()


if __name__ == '__main__':
    m = Music()
    m.set_default_search_origin(SearchOrigin.WANG_YI)
    m.search_and_download_index("消愁")
    m.close()
