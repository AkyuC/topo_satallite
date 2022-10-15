import os, sys
import time
from turtle import clear
from topo.topo import topo
from utils.genConfig import gen_diff_links2sh, gen_route2sh
from utils.cpFile import cp_sh2docker
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from controller.controller import controller


def run_shell(file):
    # 运行shell文件
    # print("run {}".format(file))
    os.system("sudo chmod +x {file}; sudo {file}".format(file=file))

def ctrl_get_slot_change(slot_no, ctrl_no):
    os.system("sudo docker exec -it s{} /bin/bash -c \"echo {} > /dev/udp/192.168.66.{}/12000\"".format(ctrl_no, slot_no, ctrl_no+1))

def db_get_slot_change(slot_no, db_no):
    os.system("sudo docker exec -it db{} /bin/bash -c \"echo {} > /dev/udp/192.168.68.{}/12000\"".format(db_no, slot_no, db_no+1))


if __name__ == "__main__":
    # 获取当前的路径
    start = time.time()
    filePath = os.getcwd()
    os.system("sudo echo start!\r")

    print("读取时间片数据!\r")
    tp = topo(filePath)

    for slot_no in range(tp.num_slot):
        print("slot_no: {}\r".format(slot_no))
        # time.sleep(30)

        print("调整路由，slot_no: {}\r".format(slot_no))
        # 告知所有的数据库
        with ThreadPoolExecutor(max_workers=tp.num_db) as pool:
            all_task = []
            for db_no in tp.db_data:
                all_task.append(pool.submit(db_get_slot_change, slot_no, db_no))
            wait(all_task, return_when=ALL_COMPLETED)
        
        time.sleep(80)

        # print("\n\r")
        # os.system("sudo python3 ./db2db_ping_test.py")
        # print("\n\r")

        print("时间片切换，slot_no: {} -> {}\r".format(slot_no, (slot_no + 1)%tp.num_slot))
        with ThreadPoolExecutor(max_workers=32) as pool:
            all_task = []
            for ctrl_no in tp.data_topos[0]:
                all_task.append(pool.submit(ctrl_get_slot_change, (slot_no + 1)%tp.num_slot, ctrl_no))
            wait(all_task, return_when=ALL_COMPLETED)
            all_task.clear()

            # 链路修改
            run_shell("{}/config/links_shell/links_add_slot{}.sh".format(tp.filePath, (slot_no + 1)%tp.num_slot))
            for sw_no in tp.data_topos[0]:
                all_task.append(pool.submit(os.system,"sudo docker exec -it s{} /bin/bash /home/config/links_shell/s{}_links_change_slot{}.sh > /dev/null".format(sw_no, sw_no, (slot_no + 1)%tp.num_slot)))
            wait(all_task, return_when=ALL_COMPLETED)
        time.sleep(5)
    # for i in range(66):
    #     print(f"s{i}:")
    #     os.system(f"sudo python3 ./sw_show_log.py {i} | grep recv\ a\ route")
    #     print(" ")