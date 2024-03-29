from requests import get
from urllib3 import exceptions, disable_warnings
from pandas import DataFrame, Series, Timestamp, concat, read_html

PROXIES = {}

TAG_DT = 'Date'
TAG_UW = 'Unit Net Worth'
TAG_TW = 'Total Net Worth'
TAG_MI = 'Million Copies Income'

class assLst:
    def __init__(self, code: str) -> None:
        self.__data = {}
        url = f'https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={code}'
        disable_warnings(exceptions.InsecureRequestWarning)
        data = get(url, proxies=PROXIES, verify=False).json()
        for detail in data['Datas']:
            if detail['CATEGORYDESC'] == '基金':
                code = detail['CODE']
                name = detail['NAME']
                typ = detail['FundBaseInfo']['FTYPE']
                self.__data[code] = {'name':name, 'type':typ}
        print(f'search [{code}]')
        return

    @property
    def data(self) -> dict[str:dict[str:str]]:
        return self.__data

class assDat:
    def __init__(
        self,
        code: str,
        sdate: Timestamp | None = None,
        edate: Timestamp | None = None
    ) -> None:
        MIN_DAYS = 148
        d = MIN_DAYS
        if sdate is not None:
            if edate is not None:
                d = (edate - sdate).days
            else:
                d = (Timestamp.now() - sdate).days
        if d < MIN_DAYS:
            func = [self.__eastmoney, self.__doctorxiong]
        else:
            func = [self.__doctorxiong, self.__eastmoney]
        self.__code = ''
        self.__name = ''
        self.__type = ''
        self.__mci = DataFrame()
        self.__nws = DataFrame()
        try:
            print(func[0].__name__, code)
            func[0](code, sdate, edate)
        except:
            print(func[1].__name__, code)
            func[1](code, sdate, edate)
        return

    def __doctorxiong(
        self,
        code: str,
        sdate: Timestamp | None = None,
        edate: Timestamp | None = None
    ) -> None:
        TAG_UNW = 'netWorthData'
        TAG_TNW = 'totalNetWorthData'
        TAG_MCI = 'millionCopiesIncomeData'
        COL_TYP = {
            0:'datetime64[ns]',
            1:'float64'
        }
        url = f'https://api.doctorxiong.club/v1/fund/detail?code={code}'
        if sdate is not None:
            url += f'&startDate={sdate.strftime(r"%Y-%m-%d")}'
        if edate is not None:
            url += f'&endDate={edate.strftime(r"%Y-%m-%d")}'
        disable_warnings(exceptions.InsecureRequestWarning)
        data = get(url, proxies=PROXIES, verify=False).json()
        err = data['code']
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
        data = data['data']
        self.__code = data['code']
        self.__name = data['name']
        self.__type = data['type']
        if TAG_UNW in data:
            unw = DataFrame(data[TAG_UNW]).astype(COL_TYP).dropna().drop_duplicates(0)
            tnw = DataFrame(data[TAG_TNW]).astype(COL_TYP).dropna().drop_duplicates(0)
            assert unw[0].equals(tnw[0]), f'Requested data mismatches [{self.__code}]'
            df = concat([unw.iloc[:, :2], tnw[1]], axis=1)
            df.columns = [TAG_DT, TAG_UW, TAG_TW]
            if sdate is not None:
                df = df[df[TAG_DT] >= sdate]
            if edate is not None:
                df = df[df[TAG_DT] <= edate]
            self.__nws = df.sort_values(TAG_DT, ignore_index=True)
        elif TAG_MCI in data:
            df = DataFrame(data[TAG_MCI]).astype(COL_TYP).dropna().drop_duplicates(0)
            df.columns = [TAG_DT, TAG_MI]
            if sdate is not None:
                df = df[df[TAG_DT] >= sdate]
            if edate is not None:
                df = df[df[TAG_DT] <= edate]
            self.__mci = df.sort_values(TAG_DT, ignore_index=True)
        else:
            raise ValueError('Unsupported data type.')
        return

    def __eastmoney(
        self,
        code: str,
        sdate: Timestamp | None = None,
        edate: Timestamp | None = None
    ) -> None:
        url = f'https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={code}'
        disable_warnings(exceptions.InsecureRequestWarning)
        data = get(url, proxies=PROXIES, verify=False).json()
        for detail in data['Datas']:
            if detail['CATEGORYDESC'] == '基金':
                self.__code = detail['CODE']
                self.__name = detail['NAME']
                self.__type = detail['FundBaseInfo']['FTYPE']
                break

        TAG_DAT = '净值日期'
        TAG_UNW = '单位净值'
        TAG_MCI = '每万份收益'
        COL_TYP = {TAG_DAT:'datetime64[ns]'}
        PER = 49
        page = 1
        pages = 1
        url = f'https://fundf10.eastmoney.com/F10DataApi.aspx?type=lsjz&code={code}&per={PER}'
        if sdate is not None:
            url += f'&sdate={sdate.strftime(r"%Y-%m-%d")}'
        if edate is not None:
            url += f'&edate={edate.strftime(r"%Y-%m-%d")}'
        HEADERS = {
            'Host': 'fundf10.eastmoney.com',
            'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36'
        }
        df = DataFrame()
        while page <= pages:
            data = get(f'{url}&page={page}', headers=HEADERS, proxies=PROXIES, verify=False).text
            df = concat([df, read_html(data)[0]])
            pages = int(data.split(',')[2][6:])
            page += 1
        if pages < 1:
            df = df.drop(df.index)
        if df.columns[1] == TAG_UNW:
            df = df.iloc[:, :3].astype(COL_TYP).dropna().drop_duplicates(TAG_DAT)
            df.columns = [TAG_DT, TAG_UW, TAG_TW]
            if sdate is not None:
                df = df[df[TAG_DT] >= sdate]
            if edate is not None:
                df = df[df[TAG_DT] <= edate]
            self.__nws = df.sort_values(TAG_DT, ignore_index=True)
        elif df.columns[1] == TAG_MCI:
            df = df.iloc[:, :2].astype(COL_TYP).dropna().drop_duplicates(TAG_DAT)
            df.columns = [TAG_DT, TAG_MI]
            if sdate is not None:
                df = df[df[TAG_DT] >= sdate]
            if edate is not None:
                df = df[df[TAG_DT] <= edate]
            self.__mci = df.sort_values(TAG_DT, ignore_index=True)
        else:
            raise ValueError('Unsupported data type.')
        return

    @property
    def code(self) -> str:
        return self.__code

    @property
    def name(self) -> str:
        return self.__name

    @property
    def type(self) -> str:
        return self.__type

    @property
    def netWorth(self) -> DataFrame:
        return self.__nws.copy()

    @property
    def MCIncome(self) -> DataFrame:
        return self.__mci.copy()

def trade_dates(
    sdate: Timestamp | None = None,
    edate: Timestamp | None = None
) -> Series:
    url = 'https://api.doctorxiong.club/v1/stock/kline/day?code=sh000001'
    if sdate is not None:
        url += f'&startDate={sdate.strftime(r"%Y-%m-%d")}'
    if edate is not None:
        url += f'&endDate={edate.strftime(r"%Y-%m-%d")}'
    disable_warnings(exceptions.InsecureRequestWarning)
    data = get(url, proxies=PROXIES, verify=False).json()
    err = data['code']
    if err == 200:
        pass
    elif err == 400:
        raise RuntimeError('Request failed.')
    elif err == 500:
        raise RuntimeError('Internal network error.')
    else:
        raise RuntimeError('Unknown error.')
    dates = Series([d[0] for d in data['data']], dtype='datetime64[ns]')
    return dates.sort_values(ignore_index=True)

if __name__ == '__main__':
    code = '000001'
    # sdate = Timestamp('2022-11-01')
    # edate = Timestamp('2022-12-01')
    # a = assDat(code, sdate, edate)
    # a = assDat(code)
    a = assLst(code)
    print(a.data)
    # print(a.code)
    # print(a.name)
    # print(a.type)
    # print(a.netWorth)
    # print(a.MCIncome)

    # dates = trade_dates()
    # print(dates)
