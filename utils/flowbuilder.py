import os
from threading import Timer
import random

class flowbuilder:
    count = 0
    is_stoped = True

    @staticmethod
    def __random_iperf_period():
        if(flowbuilder.is_stoped):
            return False
        rs = random.sample(range(0, flowbuilder.count-1), 2)
        os.system("sudo docker exec -it s{} ping -s 65500 -c 10 192.168.66.{}"\
            .format(rs[1], rs[0]+1))
        Timer(1, flowbuilder.__random_iperf_period).start()
    
    @staticmethod
    def random_ping(num):
        # 定时随机ping
        flowbuilder.count = num
        if(not flowbuilder.is_stoped):
            return False
        flowbuilder.is_stoped = False
        Timer(1, flowbuilder.__random_iperf_period).start()

    @staticmethod
    def stop():
        flowbuilder.is_stoped = True