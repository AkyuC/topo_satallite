from threading import Thread
from time import sleep
from .timer import timer
from utils import const_command
import os, time
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from socket import *
from topo.topo import topo
import copy
from utils.flowbuilder import flowbuilder
from utils.genConfig import __a_slot_diff_links2sh, gen_diff_links2sh
from utils.sw_recover import sw_rec_add_veth, sw_rec_create_veth, sw_rec_ovs


class UdpServer:
    def __init__(self):
        #define the type of socket is IPv4 and Udp
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSocket.bind(('127.0.0.1', 12001))
    
    def recv_msg(self):
        msg, addr = self.serverSocket.recvfrom(2048)
        return msg.decode('utf-8')

def load_command():
    # 命令常量定义
    # cli命令
    const_command.cli_run_topo = 0
    const_command.cli_run_iperf = 1
    const_command.cli_sw_shutdown = 2
    const_command.cli_db_shutdown = 3
    const_command.cli_db_recover = 4
    const_command.cli_recover = 5
    const_command.cli_stop_all = 6
    # timer定时器切换命令
    const_command.timer_diff = 7
    const_command.timer_rt_diff = 8

def update_slot_diff_links2sh(slot_no, sw_fail:set, links:list, filePath):
    # 由于卫星失效，所有需要对原来链路修改的脚本进行更新
    for sw_no in links:
        for index in range(len(links[sw_no])-1, -1, -1):
            if links[sw_no][index][1] in sw_fail or links[sw_no][index][2] in sw_fail:
                del links[sw_no][index]
    __a_slot_diff_links2sh(slot_no, filePath + "/config/links_shell/" , links)
 
def sw_disable(sw_no, slot_no, sw_fail, tp:topo):
    # 使卫星交换机失效
    command = "sudo docker exec -it s{s} ovs-vsctl del-br s{s};".format(s=sw_no)
    for sw_adj in tp.data_topos[slot_no][sw_no]:
        if sw_adj in sw_fail:
            continue
        command += "sudo docker exec -it s{} /bin/bash -c \"ovs-vsctl del-port s{}-s{};ip link del s{}-s{}\";".format(sw_adj, sw_adj, sw_no, sw_adj, sw_no)
    if(sw_no in tp.db_data):
        command += "sudo docker stop db{} > /dev/null;".format(sw_no)
    command += "sudo docker stop s{s} > /dev/null;".format(s=sw_no)
    os.system(command)

def run_shell(file):
    # 运行shell文件
    # print("run {}".format(file))
    os.system("sudo chmod +x {file}; sudo {file}".format(file=file))

def ctrl_get_slot_change(slot_no, ctrl_no):
    os.system("sudo docker exec -it s{} /bin/bash -c \"echo {} > /dev/udp/192.168.66.{}/12000\"".format(ctrl_no, slot_no, ctrl_no+1))

def db_get_slot_change(slot_no, db_no):
    os.system("sudo docker exec -it db{} /bin/bash -c \"echo {} > /dev/udp/192.168.68.{}/12000\"".format(db_no, slot_no, db_no+1))


class controller:
    def __init__(self, tp: topo) -> None:
        # 加载指令
        load_command()
        self.tp = tp
        self.tp_back = copy.deepcopy(tp)
        self.filePath = tp.filePath
        # 加载时间片序列
        self.topotimer = timer(self.filePath + '/config/timeslot/timefile', 0, const_command.timer_diff)
        self.rttimer = timer(self.filePath + '/config/timeslot/timefile', 10, const_command.timer_rt_diff)
        # 接收命令的套接字
        self.socket = UdpServer()
        # 目前实效的卫星
        self.sw_fail = set()
        # 现在的时间片序号
        self.slot_now = 0
        self.start()
        # 是否进行恢复
        self.is_tp_recover = False
        self.is_db_recover = False
        self.db_disable = 0
        self.db_movement = 0

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = self.socket.recv_msg().split()
            command = list(map(int, command))

            if(command[0] == const_command.cli_run_topo):
                print("开始运行topo!\r")
                self.topotimer.start()
                self.rttimer.start()

            elif(command[0] == const_command.cli_run_iperf):
                # 开线程，随机测试路由
                if(len(command) > 1):
                    flowbuilder.service_iperf(command[1], command[2], command[3])
                else:
                    flowbuilder.service_iperf()

            elif(command[0] == const_command.cli_sw_shutdown):
                # 关闭docker，同时自动删除了链路
                # 孤岛测试
                # 数据库失效的测试
                sw_fail = set(command[1:])
                print("关闭失效卫星{}\r".format(sw_fail))
                with ThreadPoolExecutor(max_workers=self.tp.num_slot) as pool:
                    all_task = []
                    for sw_no in sw_fail:
                        all_task.append(pool.submit(sw_disable, sw_no, self.slot_now, self.sw_fail.union(sw_fail), self.tp)) 
                    wait(all_task, return_when=ALL_COMPLETED)                       
                # 更新运行的脚本
                    for slot_no in range(self.tp.num_slot):
                        all_task.append(pool.submit(update_slot_diff_links2sh, slot_no, sw_fail, self.tp.diff_topos[slot_no], self.tp.filePath))
                    wait(all_task, return_when=ALL_COMPLETED)
                # 更新失效的卫星
                self.sw_fail = self.sw_fail.union(sw_fail)
                print("关闭失效卫星{}结束\r".format(sw_fail))
            
            elif(command[0] == const_command.cli_db_shutdown):
                # 只关闭数据库docker
                command = "sudo docker stop db{}\n".format(command[1])
                os.system(command)

            elif(command[0] == const_command.cli_db_recover):
                # 设置标志
                self.is_db_recover = True
                self.db_disable = command[1]
                self.db_movement = command[2] 

            elif(command[0] == const_command.cli_stop_all):
                self.stop()
                return

            elif(command[0] ==  const_command.timer_diff):
                slot_no = command[1]   # 获取切换的时间片序号
                print("时间片切换，slot_no: {} -> {}\r".format(slot_no, (slot_no + 1)%self.tp.num_slot))
                with ThreadPoolExecutor(max_workers=self.tp.num_sw) as pool:
                    all_task = []
                    for ctrl_no in range(self.tp.num_sw):
                        if ctrl_no not in self.sw_fail:   # 失效的不告知
                            all_task.append(pool.submit(ctrl_get_slot_change, (slot_no + 1)%self.tp.num_slot, ctrl_no))
                    wait(all_task, return_when=ALL_COMPLETED)
                    all_task.clear()
                # 链路修改
                    run_shell("{}/config/links_shell/links_add_slot{}.sh".format(self.tp.filePath, (slot_no + 1)%self.tp.num_slot))
                    for sw_no in range(self.tp.num_sw):
                        if sw_no not in self.sw_fail:   # 失效的不运行
                            all_task.append(pool.submit(os.system,"sudo docker exec -it s{} /bin/bash /home/config/links_shell/s{}_links_change_slot{}.sh > /dev/null".format(sw_no, sw_no, (slot_no + 1)%self.tp.num_slot)))
                    wait(all_task, return_when=ALL_COMPLETED)
                print("时间片切换，slot_no: {} -> {}，结束\r".format(slot_no, (slot_no + 1)%self.tp.num_slot))
                self.slot_now = (slot_no + 1)%self.tp.num_slot
                # 恢复
                if(self.is_tp_recover):
                    sleep(3)
                    self.tp_recover()
                    self.is_tp_recover = False
                elif(self.is_db_recover):
                    sleep(3)
                    db_disable = self.db_disable
                    db_movement = self.db_movement
                    slot_no = self.slot_now
                    command = "sudo docker exec -it s{sw} /bin/bash -c \"ovs-vsctl del-port s{sw}-db{sw}\";\n".format(sw=db_disable)
                    os.system(command)
                    command = "sudo docker start db{db} > /dev/null; sleep 1s; sudo docker exec -it db{db} /bin/bash -c \"iptables -I INPUT -s 192.168.66.0/24 -j DROP\"; sudo {path}/config/db_conf/db_init.sh {db}; sleep 1s; sudo docker exec -it db{db} /bin/bash -c \"/home/config/db_conf/db_run.sh start {db} {slot}\""\
                            .format(db=db_disable, path=self.tp.filePath, slot=slot_no)
                    os.system(command)
                    command = "sudo docker exec -it db{db} /bin/bash -c \"/home/config/db_conf/db_run.sh redis_recover {db} 0 {db_r}; iptables -D INPUT 1\";".format(db=db_disable, db_r=db_movement+1)
                    os.system(command)
                    self.is_db_recover = False

            elif(command[0] ==  const_command.timer_rt_diff):
                slot_no = command[1]   # 获取切换的时间片，提前调整路由
                # 告知所有的数据库
                print("调整路由, slot_no； {} -> {}\r".format(slot_no, (slot_no + 1)%self.tp.num_slot))
                with ThreadPoolExecutor(max_workers=self.tp.num_db) as pool:
                    all_task = []
                    for db_no in self.tp.db_data:
                        if db_no not in self.sw_fail:   # 失效的不告知
                            all_task.append(pool.submit(db_get_slot_change, slot_no, db_no))
                    wait(all_task, return_when=ALL_COMPLETED)

    def tp_recover(self):
        # topo恢复
        print("正在进行链路恢复！slot:{}\r".format(self.slot_now))
        slot_no = self.slot_now
        start = time.time()
        with ThreadPoolExecutor(max_workers=self.tp.num_sw) as pool:
            all_task = []
        # 把链路重新恢复
            if os.path.exists(self.tp.filePath + "/config/sw_recover"):
                os.system("sudo rm -rf {}/config/sw_recover".format(self.tp.filePath))
            os.makedirs(self.tp.filePath + "/config/sw_recover")
            for db_no in self.tp.db_data:
                if db_no not in self.sw_fail:
                    all_task.append(pool.submit(sw_disable, db_no, slot_no, self.sw_fail.union(set(self.tp.db_data)), self.tp)) 
            self.sw_fail = self.sw_fail.union(set(self.tp.db_data))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for sw_no in self.sw_fail:   # 开启失效的容器
                all_task.append(pool.submit(os.system, "sudo docker start s{} > /dev/null".format(sw_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for sw_no in range(self.tp.num_sw):     # 重启ovs
                all_task.append(pool.submit(sw_rec_ovs, sw_no, sw_no not in self.sw_fail, sw_no in self.tp_back.db_data))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for sw_no in self.sw_fail:  
                all_task.append(pool.submit(sw_rec_create_veth, sw_no, slot_no, self.sw_fail, self.tp_back))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for sw_no in range(self.tp.num_sw): 
                all_task.append(pool.submit(sw_rec_add_veth, sw_no, slot_no, self.tp_back))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            gen_diff_links2sh(self.tp_back)
            print("链路恢复完成！{}\r".format(time.time() - start))
            print("开始模式切换！\r")
        # 加载控制通道路由
            for sw_no in self.tp.data_topos[0]:  # ct-db的路由读取
                all_task.append(pool.submit(os.system, "sudo docker exec -it s{} ovs-ofctl add-flows s{} /home/config/sw_route_file/fl_ct2db_s{}_slot{}".format(sw_no, sw_no, sw_no, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for sw_no in self.tp.data_topos[0]:  # db-db的路由读取
                all_task.append(pool.submit(os.system, "sudo docker exec -it s{} ovs-ofctl add-flows s{} /home/config/sw_route_file/fl_db2db_s{}_slot{}".format(sw_no, sw_no, sw_no, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            # sleep(5)    # 由于仿真运行时延的原因，需要等几秒
        # 重新启动数据库
            for db_no in self.tp.db_data:
                if db_no in self.sw_fail:
                    # all_task.append(pool.submit(os.system,"sudo {}/config/db_conf/db_init.sh {}".format(self.tp.filePath, db_no)))
                    all_task.append(pool.submit(os.system,"sudo docker start db{} > /dev/null; sleep 1s; sudo {}/config/db_conf/db_init.sh {}; sleep 1s; sudo docker exec -it db{} /bin/bash -c \"/home/config/db_conf/db_run.sh start {} {}\""\
                        .format(db_no, self.tp.filePath, db_no, db_no, db_no, slot_no)))
                else:
                    all_task.append(pool.submit(os.system,"sudo docker restart db{} > /dev/null; sleep 1s; sudo {}/config/db_conf/db_init.sh {}; sleep 1s; sudo docker exec -it db{} /bin/bash -c \"/home/config/db_conf/db_run.sh start {} {}\""\
                        .format(db_no, self.tp.filePath, db_no, db_no, db_no, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for db_no in self.tp.db_data:
                all_task.append(pool.submit(os.system,"sudo docker exec db{} /bin/bash -c \"stdbuf -oL nohup /home/monitor_new 192.168.68.{} > /home/db.log 2>&1 &\"".format(db_no, db_no+1)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
        # 重新启动控制器
            for sw_no in range(self.tp.num_sw):  
                all_task.append(pool.submit(os.system,"sudo docker exec -it s{s} /bin/bash -c \"/usr/src/openmul/mul.sh stop > /dev/null; sleep 1s; /usr/src/openmul/mul.sh start mulhello > /dev/null;\""\
                    .format(s=sw_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            sleep(5)    # 由于仿真运行时延的原因，需要等几秒
            for sw_no in range(self.tp.num_sw):  
                all_task.append(pool.submit(os.system,"sudo docker exec -it s{s} /bin/bash -c \"echo {slot} > /dev/udp/192.168.66.{ip}/12000\";sudo docker exec s{s} ovs-vsctl set-controller s{s} tcp:192.168.66.{ip}:6653 -- set bridge s{s} other_config:enable-flush=false;sudo docker exec s{s} ovs-vsctl set controller s{s} connection-mode=out-of-band"\
                    .format(s=sw_no, ip=sw_no+1, slot=slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
        # topo数据回退
        self.tp = copy.deepcopy(self.tp_back)
        self.sw_fail.clear()
        print("模式切换完成！{}\r".format(time.time() - start))
    
    def start(self):
        # 开启线程
        Thread(target=self.__do_start).start()

    def stop(self):
        # 关闭线程
        self.started = False
        self.topotimer.stop()
        self.rttimer.stop()
        os.system("stty -raw; sudo docker stop $(sudo docker ps -a -q)")
        os.system("stty -raw; sudo docker rm $(sudo docker ps -a -q)")