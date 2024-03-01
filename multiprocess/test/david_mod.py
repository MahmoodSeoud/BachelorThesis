import multiprocessing

def overlapped_thread(testClass, c, i, barrier):
    print(f"{testClass.a}, {testClass.b}, {c}, id:{i} - 1")
    barrier.wait()
    print(f"{testClass.a}, {testClass.b}, {c}, id:{i} - 2")
    barrier.wait()
    print(f"{testClass.a}, {testClass.b}, {c}, id:{i} - 3")

class TestClass():
    def __init__(self, a, b):
        self.a = a
        self.b = b

    def overlap(self, c):
        barrier = multiprocessing.Barrier(2)

        threads = [multiprocessing.Process(
                target=overlapped_thread, 
                args=(self, c, i, barrier)
            ) for i in range(2)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()


if __name__ == "__main__":
    tc = TestClass("Albert", "Brenda")
    tc.overlap("Colin")