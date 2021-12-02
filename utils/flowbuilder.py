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
        os.system("sudo docker exec -it s{} ping -s 60000 -c 3 192.168.66.{}"\
            .format(rs[1], rs[0]+1))
        # os.system("sudo docker exec -it s{} iperf -u -c 192.168.66.{} -b 10M -t 3"\
        #     .format(rs[1], rs[0]+1))
        Timer(1, flowbuilder.__random_iperf_period).start()
    
    @staticmethod
    def random_ping(sw_num=66, thread_num=1):
        # 定时随机ping
        flowbuilder.count = sw_num
        if(not flowbuilder.is_stoped):
            return False
        flowbuilder.is_stoped = False
        for i in range(thread_num):
            Timer(1, flowbuilder.__random_iperf_period).start()

    @staticmethod
    def stop():
        flowbuilder.is_stoped = True