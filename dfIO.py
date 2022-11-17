from os import path
from pandas import DataFrame, read_csv

IDX_RD = 0
IDX_WR = 1

DICT_DFIO = {
    '*.csv':  [read_csv, DataFrame.to_csv]
}

FLTR_DFIO = ';;'.join([k for k in DICT_DFIO.keys()])

FLTR_DFIO_ALL = '*.*;;' + FLTR_DFIO

def getFileTyp(file: str) -> str:
    fileNameSect = path.basename(file).split(path.extsep)
    if len(fileNameSect) > 1:
        typ = f'*.{fileNameSect[-1]}'
    else:
        typ = '*'
    return typ

def dfImport(file: str) -> DataFrame:
    typ = getFileTyp(file)
    assert typ in DICT_DFIO, f'Unsupported file format [{typ}]'
    df = DICT_DFIO[typ][IDX_RD](file)
    assert type(df) is DataFrame
    return df

def dfExport(df: DataFrame, file: str) -> None:
    typ = getFileTyp(file)
    assert typ in DICT_DFIO, f'Unsupported file format [{typ}]'
    DICT_DFIO[typ][IDX_WR](df, file, index=False)
    return
