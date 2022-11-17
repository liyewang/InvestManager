from requests import get
from urllib3 import exceptions, disable_warnings

PROXIES = {}

class assInf:
    data = {}
    def __init__(
        self,
        code: str,
        sdate: str | None = None,
        edate: str | None = None
    ) -> None:
        url = f'https://api.doctorxiong.club/v1/fund/detail?code={code}'
        if sdate is not None:
            url += f'&startDate={sdate}'
        if edate is not None:
            url += f'&endDate={edate}'
        if PROXIES:
            disable_warnings(exceptions.InsecureRequestWarning)
            self.data = get(url, proxies=PROXIES, verify=False).json()
        else:
            self.data = get(url).json()
        err = self.data['code']
        if err == 200:
            pass
        elif err == 400:
            raise RuntimeError('Request failed.')
        elif err == 405:
            raise ValueError(f'Invalid asset code [{code}]')
        elif err == 500:
            raise RuntimeError('Internal network error.')
        else:
            raise RuntimeError('Unknown error.')
        return

    @property
    def code(self) -> str:
        return self.data['data']['code']

    @property
    def name(self) -> str:
        return self.data['data']['name']

    @property
    def unitNetWorth(self) -> list:
        return self.data['data']['netWorthData']

    @property
    def totalNetWorth(self) -> list:
        return self.data['data']['totalNetWorthData']

if __name__ == '__main__':
    code = '000001'
    sdate = '2022-11-01'
    edate = '2022-12-01'
    a = assInf(code, sdate, edate)
    print(a.totalNetWorth)



# def getFundVal_eastmoney(code: str, start: Timestamp, end: Timestamp) -> DataFrame:
#     sdate = start.strftime(r'%Y-%m-%d')
#     edate = end.strftime(r'%Y-%m-%d')
#     per = 49
#     page = 1
#     pages = 1
#     DATE = '净值日期'
#     df = DataFrame()
#     while page <= pages:
#         txt = get(
#             f'https://fundf10.eastmoney.com/F10DataApi.aspx?type=lsjz&code={code}&page={page}&sdate={sdate}&edate={edate}&per={per}',
#             headers={
#                 'Host': 'fundf10.eastmoney.com',
#                 'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
#             }
#         ).text
#         df = concat([df, read_html(txt)[0]])
#         pages = int(txt.split(',')[2][6:])
#         print(page)
#         page += 1
#     return df.iloc[:, :3].astype({DATE:'datetime64[ns]'}).drop_duplicates(DATE).sort_values(DATE, ascending=False, ignore_index=True)

# code = '000001'
# start = Timestamp('2022-10-01')
# end = Timestamp('2022-11-01')
# try:
#     tab = getFundVal_eastmoney(code, start, end)
# except:
#     raise
# print(tab)
# print(tab.dtypes)



# df = read_xml(get(
#     f'http://data.funds.hexun.com/outxml/detail/openfundnetvalue.aspx?fundcode={code}',
#     headers={'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36'}
# ).text)
# code_new = f'{df.iat[0, 0]:06.0f}'
# if code_new != code:
#     raise ValueError(f'Asset code [{code_new}] mismatches the group code [{code}].')
# self.__code = code_new
# self.__name = df.iat[1, 1]
# DATE = 'fld_enddate'
# self.__tab = df.iloc[2:, 2:5].astype({DATE:'datetime64[ns]'}).drop_duplicates(DATE) \
#     .sort_values(DATE, ascending=False, ignore_index=True)
# self.__tab = concat([self.__tab, DataFrame(
#     [[0., 0., NAN, NAN, NAN, NAN]], range(self.__tab.index.size))], axis=1)
# self.__tab.columns = COL_TAG