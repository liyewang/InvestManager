
from functools import wraps
from time import time

alldata = []

class timer:
    total = 0.
    ls = []
    name = ''

    def __init__(self, mute: bool = False) -> None:
        self.__mute = mute
        return

    def __call__(self, func):
        self.name = func.__name__
        @wraps(func)
        def wrapped_func(*args, **kwargs):
            t = time()
            ret = func(*args, **kwargs)
            t = time() - t
            self.ls.append(t)
            self.total += t
            return ret
        return wrapped_func

    def __del__(self) -> None:
        count = len(self.ls)
        avg = self.total / count
        alldata.append([self.name, self.ls, self.total, count, avg])
        if self.__mute:
            return
        print('\nTimer records:')
        for i in range(count):
            print(f'{i+1:10d}:\t{self.ls[i]:15.9f} seconds')
        print(f'\nFunction:\t\t{self.name}')
        print(f'Call:\t\t{count:15d} times')
        print(f'Total:\t\t{self.total:15.9f} seconds')
        print(f'Average:\t{avg:15.9f} seconds\n')
        return

if __name__ == '__main__':
    @timer()
    def test1(a):
        print('test1')
        for i in range(a):
            pass

    @timer()
    def test2():
        for i in range(1000000):
            pass

    test1(1000000)
    test1(10000000)
    test2()
    del test1
    del test2
    print(alldata)
