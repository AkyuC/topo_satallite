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
    const_command.cli_fail_link = 3
    const_command.cli_recover_link = 4
    const_command.cli_db_shutdown = 5
    const_command.cli_db_recover = 6
    const_command.cli_recover = 7
    const_command.cli_stop_all = 9
    # timer定时器切换命令
    const_command.timer_diff = 100
    # const_command.timer_rt_diff = 9

def update_slot_diff_links2sh(slot_no, sw_fail:set, links:list, filePath):
    # 由于卫星失效，所有需要对原来链路修改的脚本进行更新
    for sw_no in links:
        for index in range(len(links[sw_no])-1, -1, -1):
            if links[sw_no][index][1] in sw_fail or links[sw_no][index][2] in sw_fail:
                del links[sw_no][index]
    __a_slot_diff_links2sh(slot_no, filePath + "/config/links_shell/" , links)

def update_slot_diff_links2sh_link_del(slot_no, sw1, sw2, links:list, filePath):
    # 由于链路失效，所有需要对原来链路修改的脚本进行更新
    for index in range(len(links[sw1])-1, -1, -1):
        if links[sw1][index][1] == sw2:
            del links[sw1][index]
    for index in range(len(links[sw2])-1, -1, -1):
        if links[sw2][index][1] == sw1:
            del links[sw2][index]
    __a_slot_diff_links2sh(slot_no, filePath + "/config/links_shell/" , links)

def update_slot_diff_links2sh_link_add(slot_no, sw1, sw2, links:list, delay, filePath):
    # 由于链路恢复，所有需要对原来链路修改的脚本进行更新
    links[sw1][sw2] = delay
    links[sw2][sw1] = delay
    __a_slot_diff_links2sh(slot_no, filePath + "/config/links_shell/" , links)

def link_add2topo(sw1, sw2, delay):
    # 添加链路到运行的拓扑当中
    p1 = "s{}-s{}".format(sw1,sw2)
    p2 = "s{}-s{}".format(sw2,sw1)
    command = "sudo ip link add {} type veth peer name {} > /dev/null\n".format(p1, p2)
    command += "sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up > /dev/null\n".format(p1, p1, sw1)
    command += "sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up > /dev/null\n".format(p2, p2, sw2)
    command += "sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw1, p1, int(delay*1000))
    command += "sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw2, p2, int(delay*1000))
    command += "sudo docker exec -it s{} ip link set {} up > /dev/null\n".format(sw1, p1)
    command += "sudo docker exec -it s{} ip link set {} up > /dev/null\n".format(sw2, p2)
    command += "sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n".format(sw1, sw1, p1, p1, sw2+1000)
    command += "sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n".format(sw2, sw2, p2, p2, sw1+1000)
    os.system(command)
 
def sw_disable(sw_no, slot_no, sw_fail, tp:topo):
    # 使卫星交换机失效
    command = "sudo docker exec -it s{s} ovs-vsctl del-br s{s};".format(s=sw_no)
    os.system(command)
    # sleep(0.5)
    for sw_adj in tp.data_topos[slot_no][sw_no]:
        if sw_adj in sw_fail:
            continue
        command = "sudo docker exec -it s{} /bin/bash -c \"ovs-vsctl del-port s{}-s{};ip link del s{}-s{}\" > /dev/null;".format(sw_adj, sw_adj, sw_no, sw_adj, sw_no)
        os.system(command)
        sleep(1)
    if(sw_no in tp.db_data):
        command = "sudo docker stop db{} > /dev/null;".format(sw_no)
        os.system(command)
    command = "sudo docker stop s{s} > /dev/null;".format(s=sw_no)
    os.system(command)

def run_shell(file):
    # 运行shell文件
    # print("run {}".format(file))
    os.system("sudo chmod +x {file}; sudo {file} > /dev/null".format(file=file))

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
        # self.rttimer = timer(self.filePath + '/config/timeslot/timefile', 10, const_command.timer_rt_diff)
        # 接收命令的套接字
        self.socket = UdpServer()
        # 目前失效的卫星
        self.sw_fail = set()
        # 目前失效的数据库
        self.db_fail = set()
        # 目前失效的数据库
        self.link_fail = set()
        # 现在的时间片序号
        self.slot_now = 0
        
        # 是否进行恢复
        self.is_tp_recover = False
        self.is_db_recover = False
        self.db_disable = 0
        self.db_movement = 0

        self.start()

    def __do_start(self):
        # 控制器从消息队列中获取指令，并且执行对应的函数
        while True:
            command = self.socket.recv_msg().split()
            command = list(map(int, command))

            if(command[0] == const_command.cli_run_topo):
                print("开始运行topo!\r")
                self.topotimer.start()
                with ThreadPoolExecutor(max_workers=self.tp.num_db) as pool:
                    all_task = []
                    for db_no in self.tp.db_data:
                        all_task.append(pool.submit(db_get_slot_change, 0, db_no))
                    wait(all_task, return_when=ALL_COMPLETED)
                # self.rttimer.start()

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
                with ThreadPoolExecutor(max_workers=32) as pool:
                    all_task = []
                    for sw_no in sw_fail:
                        if sw_no in self.tp.db_data:
                            self.db_fail.add(sw_no)
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
                if command[1] not in self.tp.db_data:
                    continue
                print("仅失效数据库db{}\r".format(command[1]))
                self.db_fail.add(command[1])
                command = "sudo docker stop db{} > /dev/null\n".format(command[1])
                os.system(command)
            
            elif(command[0] == const_command.cli_fail_link):
                sw1 = command[1]
                sw2 = command[2]
                if (sw1, sw2) in self.link_fail or (sw2, sw1) in self.link_fail:
                    continue
                self.link_fail.add((sw1,sw2))
                print("失效链路sw{}-sw{}\r".format(sw1, sw2))
                command = "sudo docker exec -it s{} /bin/bash -c \"ovs-vsctl del-port s{}-s{};ip link del s{}-s{}\";".format(sw1, sw1, sw2, sw1, sw2)
                command += "sudo docker exec -it s{} /bin/bash -c \"ovs-vsctl del-port s{}-s{}\";".format(sw2, sw2, sw1)
                os.system(command)
                # 链路失效
                with ThreadPoolExecutor(max_workers=32) as pool:
                    all_task = []                     
                # 更新运行的脚本
                    for slot_no in range(self.tp.num_slot):
                        all_task.append(pool.submit(update_slot_diff_links2sh_link_del, slot_no, sw1, sw2, self.tp.diff_topos[slot_no], self.tp.filePath))
                    wait(all_task, return_when=ALL_COMPLETED)

            elif(command[0] == const_command.cli_recover_link):
                sw1 = command[1]
                sw2 = command[2]
                try:
                    self.link_fail.remove((sw1, sw2))
                    self.link_fail.remove((sw2, sw1))
                except KeyError:
                    pass
                slot_no = self.slot_now
                if sw2 in self.tp_back.data_topos[slot_no][sw1] and sw1 not in self.sw_fail and sw2 not in self.sw_fail:
                    print("恢复链路sw{}-sw{}\r".format(sw1, sw2))
                    with ThreadPoolExecutor(max_workers=32+1) as pool:
                        all_task = []
                        all_task.append(pool.submit(link_add2topo, sw1, sw2, self.tp_back.data_topos[slot_no][sw1][sw2]))
                    # 更新运行的脚本
                        for slot_no in range(self.tp.num_slot):
                            all_task.append(pool.submit(update_slot_diff_links2sh_link_add, slot_no, sw1, sw2, self.tp.diff_topos[slot_no], self.tp_back.data_topos[slot_no][sw1][sw2], self.tp.filePath))
                        wait(all_task, return_when=ALL_COMPLETED)


            elif(command[0] == const_command.cli_db_recover):
                # 设置标志
                self.is_db_recover = True
                self.db_disable = command[1]
                self.db_movement = command[2] 
            
            elif(command[0] == const_command.cli_recover):
                # 设置标志
                self.is_tp_recover = True

            elif(command[0] == const_command.cli_stop_all):
                self.stop()
                return

            elif(command[0] ==  const_command.timer_diff):
                slot_no = command[1]   # 获取切换的时间片序号
                self.slot_now = (slot_no + 1)%self.tp.num_slot
                
                print("时间片切换，slot_no: {} -> {}\r".format(slot_no, (slot_no + 1)%self.tp.num_slot))
                with ThreadPoolExecutor(max_workers=32) as pool:
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
                # print("时间片切换，slot_no: {} -> {}，结束\r".format(slot_no, (slot_no + 1)%self.tp.num_slot))
                # 恢复
                if(self.is_tp_recover):
                    sleep(3)
                    self.tp_recover()
                    self.is_tp_recover = False
                    self.is_db_recover = False
                    continue

                print("调整路由, slot_no：{}\r".format(self.slot_now))
                with ThreadPoolExecutor(max_workers=self.tp.num_db) as pool:
                    all_task = []
                    for db_no in self.tp.db_data:
                        if db_no not in self.db_fail:   # 失效的不告知
                            all_task.append(pool.submit(db_get_slot_change, self.slot_now, db_no))
                    wait(all_task, return_when=ALL_COMPLETED)
                
                if(self.is_db_recover):
                    sleep(10)
                    db_disable = self.db_disable
                    db_movement = self.db_movement
                    print("从db{}中拉取数据到db{}\r".format(db_movement, db_disable))
                    slot_no = self.slot_now
                    command = "sudo docker exec -it s{sw} /bin/bash -c \"ovs-vsctl del-port s{sw}-db{sw}\";\n".format(sw=db_disable)
                    os.system(command)
                    command = "sudo docker start db{db} > /dev/null; sleep 1s; sudo docker exec -it db{db} /bin/bash -c \"iptables -I INPUT -s 192.168.66.0/24 -j DROP\"; sudo {path}/config/db_conf/db_init.sh {db}; sleep 1s; sudo docker exec -it db{db} /bin/bash -c \"/home/config/db_conf/db_run.sh start {db} {slot}\""\
                            .format(db=db_disable, path=self.tp.filePath, slot=slot_no)
                    os.system(command)
                    command = "sudo docker exec -it db{db} /bin/bash -c \"/home/config/db_conf/db_run.sh redis_recover {db} 0 {db_r}; iptables -D INPUT 1; rm /home/config/db_conf/db{db}.log; sleep 1s;\";".format(db=db_disable, db_r=db_movement+1)
                    os.system(command)
                    # os.system("sudo docker exec db{} /bin/bash -c \"stdbuf -oL nohup /home/monitor_new 192.168.68.{} > /home/config/db_conf/db{}.log 2>&1 &\"".format(db_disable, db_disable+1, db_disable))
                    all_task = []
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        all_task.append(pool.submit(os.system,"sudo docker exec db{} /bin/bash -c \"stdbuf -oL nohup /home/monitor_new 192.168.68.{} > /home/config/db_conf/db{}.log 2>&1 &\"".format(db_disable, db_disable+1, db_disable)))
                    wait(all_task, return_when=ALL_COMPLETED)
                    self.is_db_recover = False
                    self.db_fail.remove(db_disable)
                    print("从db{}中拉取数据到db{} end\r".format(db_movement, db_disable))

    def tp_recover(self):
        # topo恢复
        print("正在进行链路恢复！slot:{}\r".format(self.slot_now))
        slot_no = self.slot_now
        start = time.time()
        with ThreadPoolExecutor(max_workers=32) as pool:
            all_task = []
            # 把链路重新恢复
            if os.path.exists(self.tp.filePath + "/config/sw_recover"):
                os.system("sudo rm -rf {}/config/sw_recover".format(self.tp.filePath))
            os.makedirs(self.tp.filePath + "/config/sw_recover")
            for (sw1, sw2) in self.link_fail:
                if (sw1 not in self.sw_fail) and (sw2 not in self.sw_fail) and (sw2 in self.tp_back.data_topos[slot_no][sw1]):
                    link_add2topo(sw1, sw2, self.tp_back.data_topos[slot_no][sw1][sw2])
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
            for sw_no in self.tp.data_topos[0]:  # db-db的路由读取
                all_task.append(pool.submit(os.system, "sudo docker exec -it s{} ovs-ofctl add-flows s{} /home/config/sw_route_file/fl_db2db_s{}_slot{}".format(sw_no, sw_no, sw_no, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for sw_no in self.tp.data_topos[0]:  # ct-db的路由读取
                all_task.append(pool.submit(os.system, "sudo docker exec -it s{} ovs-ofctl add-flows s{} /home/config/sw_route_file/fl_ct2db_s{}_slot{}".format(sw_no, sw_no, sw_no, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            # 重新启动数据库
            for db_no in self.tp.db_data:
                if db_no in self.db_fail:
                    # all_task.append(pool.submit(os.system,"sudo {}/config/db_conf/db_init.sh {}".format(self.tp.filePath, db_no)))
                    all_task.append(pool.submit(os.system,"sudo docker start db{} > /dev/null; sleep 1s; sudo {}/config/db_conf/db_init.sh {}".format(db_no, self.tp.filePath, db_no)))
                else:
                    all_task.append(pool.submit(os.system,"sudo docker restart db{} > /dev/null; sleep 1s; sudo {}/config/db_conf/db_init.sh {}".format(db_no, self.tp.filePath, db_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            for db_no in self.tp.db_data:
                all_task.append(pool.submit(os.system,"sudo docker exec -it db{} /bin/bash -c \"/home/config/db_conf/db_run.sh start {} {}; sleep 1s;\"".format(db_no, db_no, slot_no)))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
            time.sleep(5)
            os.system("sudo docker exec -it db{} /bin/bash -c \"/home/config/db_conf/init_map {} 192.168.68.{} > /dev/null\"".format(13, slot_no, 14))
            for db_no in self.tp.db_data:
                all_task.append(pool.submit(os.system,"sudo docker exec db{} /bin/bash -c \"stdbuf -oL nohup /home/monitor_new 192.168.68.{} > /home/config/db_conf/db{}.log 2>&1 &\"".format(db_no, db_no+1, db_no)))
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
        self.db_fail.clear()
        self.link_fail.clear()
        # 通告时间片
        with ThreadPoolExecutor(max_workers=32) as pool:
            all_task = []
            for ctrl_no in range(self.tp.num_sw):
                all_task.append(pool.submit(ctrl_get_slot_change, slot_no, ctrl_no))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()
        with ThreadPoolExecutor(max_workers=self.tp.num_db) as pool:
            all_task = []
            for db_no in self.tp.db_data:
                all_task.append(pool.submit(db_get_slot_change, slot_no, db_no))
            wait(all_task, return_when=ALL_COMPLETED)

        print("模式切换完成！{}\r".format(time.time() - start))
    
    def start(self):
        # 开启线程
        Thread(target=self.__do_start).start()

    def stop(self):
        # 关闭线程
        self.started = False
        self.topotimer.stop()
        os.system("stty -raw; sudo docker stop $(sudo docker ps -a -q)")
        os.system("stty -raw; sudo docker rm $(sudo docker ps -a -q)")
        os.system("stty -raw; sudo kill -s 9 `ps -aux | grep run.py | awk '{print $2}'`  > /dev/null")