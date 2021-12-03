from concurrent.futures import thread
import os
from threading import Thread
import random

class flowbuilder:
    count = 66

    @staticmethod
    def __random_iperf_period(sw1=-1, sw2=-1, t=10):
        # os.system("sudo docker exec -it s{} ping -s 60000 -c 3 192.168.66.{}"\
        #     .format(rs[1], rs[0]+1))
        os.system("sudo docker exec -it s{} iperf -s -u &; sudo docker exec -it s{} iperf -u -c 192.168.66.{} -b 10M -t {}"\
            .format(sw2, sw1, sw2+1, t))
    
    @staticmethod
    def random_ping(sw1=-1, sw2=-1, t=10):
        # 定时随机ping
        if(sw1 == -1):
            rs = random.sample(range(0, flowbuilder.count-1), 2)
            sw1 = rs[0]
            sw2 = rs[1]
        Thread(flowbuilder.__random_iperf_period, sw1, sw2, t).start()