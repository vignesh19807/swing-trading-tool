from concurrent.futures import ProcessPoolExecutor
def init():
    pass
def work(x):
    return x * 2

if __name__ == '__main__':
    with ProcessPoolExecutor(max_workers=2, initializer=init) as p:
        res = list(p.map(work, [1, 2, 3]))
        print("Result:", res)

