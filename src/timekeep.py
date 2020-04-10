import datetime
from Utils import getTimeDelta

class Timekeeper:
    def __init__(self):
        self.start_time = datetime.datetime.now()

    def uptime(self):
        curr_time = datetime.datetime.now()
        days, hours, minutes = getTimeDelta(curr_time, self.start_time)
        mes = "I have been running for {} days, {} hours, and {} minutes".format(days, hours, minutes)

        return mes
