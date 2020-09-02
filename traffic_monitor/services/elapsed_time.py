import time


class ElapsedTime:
    """
    Timer the counts elapsed time.
    Usage:
    # create a timer
    timer = ElapsedTime()
    # get the elapsed time
    seconds_since_timer_started = timer.get()
    # start the timer at 0
    timer.reset()

    """
    def __init__(self, start_time=time.perf_counter(), adj=0):
        self.start_time = start_time + adj

    def get(self):
        return time.perf_counter() - self.start_time

    def reset(self):
        self.start_time = time.perf_counter()

    def __str__(self):
        t = self.get()
        s = int(t % 60)
        m = int((t / 60) % 60)
        h = int((t / (60 * 60)) % 60)
        return "{:02}:{:02}:{:02}".format(h, m, s)

    def __round__(self, x):
        return self.__str__()
