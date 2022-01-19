import os
from threading import Thread
import functools
print = functools.partial(print, end='')

from socket import *
class UdpClient:
    serverName = '127.0.0.1'
    serverPort = 12001
    socketAddress = (serverName, serverPort)
    def __init__(self):
        #define the type of socket is IPv4 and Udp
        self.clientSocket = socket(AF_INET, SOCK_DGRAM)
    
    def sent_msg(self, msg:str):
        self.clientSocket.sendto(msg.encode('utf-8'), self.socketAddress)

class cli:
    def __init__(self) -> None:
        # 初始化
        self.status = False # 状态变量
        self.socket = UdpClient()
        self.start()

    def __do_start(self):
        # cli界面线程
        os.system("clear")
        while True:
            try:
                print(">-- Available commands:\n"
                    ">-- 0.run topo\n"
                    ">-- 1.run service(sw1, sw2, time)(random_sw1, random_sw2, 10s)\n"
                    ">-- 2.sw shutdown + sw number(0 ~ 65)\n"
                    ">-- 3.db shutdown but sw is online (13, 16, 31, 46, 50, 54)\n"
                    ">-- 4.db recover, two db num(13, 16, 31, 46, 50, 54)\n"
                    ">-- 5.topo recover\n"
                    ">-- 6.stop all and exit\n"
                    )

                command = input(">Input commands:\n").strip()
                print('\n')
                if len(command) == 0:
                    print("请正确输入！\n")
                    continue
                # 写入消息队列中
                self.socket.sent_msg(command)
                if(int(command[0]) == 6):
                    self.stop()
                    break
                
            except KeyboardInterrupt:
                # 键盘输入错误，关闭所有的设备，退出
                print("Error input! Exit！\n")
                # 通知其他线程关闭
                break
    
    def start(self):
        # 开启线程
        if self.status:
            return False
        else:
            Thread(target=self.__do_start).start()
            self.status = True
        return True

    def stop(self):
        # 关闭线程
        self.socket.sent_msg(str(7))


if __name__ == '__main__' :
    # cli加载
    user_cli = cli()