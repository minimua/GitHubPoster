import pendulum
import requests

from github_poster.loader.base_loader import BaseLoader
from github_poster.loader.config import WEREAD_BASE_URL, WEREAD_HISTORY_URL


class WereadLoader(BaseLoader):
    track_color = "#2EA8F7"
    unit = "mins"

    def __init__(self, from_year, to_year, _type, **kwargs):
        super().__init__(from_year, to_year, _type)
        self.weread_cookie = kwargs.get("weread_cookie", "")
        self.session = requests.Session()
        self._make_years_list()

    @classmethod
    def add_loader_arguments(cls, parser, optional):
        parser.add_argument(
            "--weread_cookie",
            dest="weread_cookie",
            type=str,
            required=optional,
            help="",
        )

    def get_api_data(self):
        print("开始获取微信读书API数据...")
        r = self.session.get(WEREAD_HISTORY_URL)
        print(f"API响应状态码: {r.status_code}")
        if not r.ok:
            print(f"API响应内容: {r.text}")
            # need to refresh cookie WTF the design!!
            if r.json()["errcode"] == -2012:
                print("需要刷新cookie，尝试重新获取...")
                self.session.get(WEREAD_BASE_URL)
                r = self.session.get(WEREAD_HISTORY_URL)
                print(f"刷新后的API响应状态码: {r.status_code}")
            else:
                raise Exception("Can not get weread history data")
        return r.json()

    def make_track_dict(self):
        print("开始处理微信读书数据...")
        api_data = self.get_api_data()
        print(f"API返回的数据结构: {list(api_data.keys())}")
        month_data = api_data["datas"]
        print(f"获取到的月度数据数量: {len(month_data)}")
        for m in month_data:
            m_start_date = pendulum.from_timestamp(
                m["baseTimestamp"], tz=self.time_zone
            )
            read_time_list = m["timeMeta"]["readTimeList"]
            if not sum(read_time_list):
                continue
            m_end_date = m_start_date.end_of("month")
            m_date_list = list(pendulum.interval(m_start_date, m_end_date))
            for k, v in zip(m_date_list, read_time_list):
                self.number_by_date_dict[k.to_date_string()] = round(v / 60.0, 2)
        for _, v in self.number_by_date_dict.items():
            self.number_list.append(v)

    def get_all_track_data(self):
        self.session.cookies = self.parse_cookie_string(self.weread_cookie)
        self.make_track_dict()
        self.make_special_number()
        return self.number_by_date_dict, self.year_list
