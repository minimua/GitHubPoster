import json
import os
import time
from collections import defaultdict

import pendulum
import requests

from github_poster.loader.base_loader import BaseLoader, LoadError
from github_poster.loader.config import BILIBILI_HISTORY_URL


class BilibiliLoader(BaseLoader):
    track_color = "#FB7299"
    unit = "videos"

    def __init__(self, from_year, to_year, _type, **kwargs):
        super().__init__(from_year, to_year, _type)
        self.number_by_date_dict = defaultdict(int)
        self.session = requests.Session()
        self.bilibili_cookie = kwargs.get("bilibili_cookie", "")
        self.bilibili_file = kwargs.get("bilibili_history_file")
        self._parse_bilibili_history()

    @classmethod
    def add_loader_arguments(cls, parser, optional):
        parser.add_argument(
            "--bilibili_cookie",
            dest="bilibili_cookie",
            type=str,
            required=optional,
            help="The cookie for the bilibili website(XHR)",
        )
        parser.add_argument(
            "--bilibili_history_file",
            dest="bilibili_history_file",
            type=str,
            default=os.path.join("IN_FOLDER", "bilibili-history.json"),
            help="bilibili history file path",
        )

    def _parse_bilibili_history(self):
        if os.path.exists(self.bilibili_file):
            with open(self.bilibili_file, "r") as f:
                self.number_by_date_dict = json.load(f)

    def _writeback_bilibili_history(self):
        with open(self.bilibili_file, "w") as f:
            json.dump(self.number_by_date_dict, f, sort_keys=True)

    def get_api_data(self, max_oid="", view_at="", data_list=[]):
        print("开始获取Bilibili API数据...")
        url = BILIBILI_HISTORY_URL.format(max_oid=max_oid, view_at=view_at)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.bilibili.com/",
            "Accept": "application/json, text/plain, */*",
            "Connection": "keep-alive",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        }

        r = self.session.get(
            url
        )

        print(f"API响应状态码: {r.status_code}")
        if not r.ok:
            print(f"API响应内容: {r.text}")
            raise LoadError(
                "Can not get bilibili history data, please check your cookie"
            )
        data = r.json()["data"]
        print(f"API返回的数据结构: {list(data.keys())}")
        if not data["list"]:
            return data_list
        lst = data["list"]
        print(f"本次获取到的数据条数: {len(lst)}")
        max_oid = lst[-1]["history"]["oid"]
        view_at = lst[-1]["view_at"]
        data_list.extend(lst)
        # spider rule
        time.sleep(2)
        return self.get_api_data(max_oid=max_oid, view_at=view_at, data_list=data_list)

    def make_track_dict(self):
        print("开始处理Bilibili数据...")
        data_list = self.get_api_data()
        print(f"总共获取到的数据条数: {len(data_list)}")
        new_watch_dict = defaultdict(int)
        for d in data_list:
            date_str = pendulum.from_timestamp(
                d["view_at"], tz=self.time_zone
            ).to_date_string()
            new_watch_dict[date_str] += 1
        for i in new_watch_dict:
            if (
                i not in self.number_by_date_dict
                or new_watch_dict[i] != self.number_by_date_dict[i]
            ):
                self.number_by_date_dict[i] = new_watch_dict[i]
        self._writeback_bilibili_history()
        for _, v in self.number_by_date_dict.items():
            self.number_list.append(v)

    def get_all_track_data(self):
        # first we need to activate the session with cookie str from `chrome`
        self.session.cookies = self.parse_cookie_string(self.bilibili_cookie)

        self.make_track_dict()
        self.make_special_number()
        return self.number_by_date_dict, self.year_list
