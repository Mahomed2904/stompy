import time
import threading


class ScheduleTimer:

    # Static vars
    __count: int = 1

    # Local vars
    id: int = 0
    continue_running: bool = False

    def __init__(self, continue_running=False):
        self.id = ScheduleTimer.__count
        ScheduleTimer.__count += 1
        self.continue_running = continue_running


def setTimeout(callback, timeout):
    timer = ScheduleTimer(True)
    def fun(timer):
        time.sleep(timeout/1000)
        if timer.continue_running:
            callback()
    threading.Thread(target=fun, args=(timer,), name=f"setTimeout-{timer.id}", daemon=True).start()
    return timer


def setInterval(callback, interval):
    timer = ScheduleTimer(True)
    def fun(timer):
        while timer.continue_running:
            time.sleep(interval/1000)
            if timer.continue_running:
                callback()
    threading.Thread(target=fun, args=(timer,), name=f"setInterval-{ScheduleTimer.id}", daemon=True).start()
    return timer


def clearInterval(timer):
    timer.continue_running = False


def clearTimeout(timer):
    timer.continue_running = False

