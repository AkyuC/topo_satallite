import os
import time
from topo.topo import topo
from utils.genConfig import gen_diff_links2sh, gen_route2sh
from utils.cpFile import cp_sh2docker
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from controller.controller import controller


if __name__ == "__main__":
    # 获取当前的路径
    os.system("sudo echo start!")
    start = time.time()
    filePath = os.getcwd()

    print("读取时间片数据!\r")
    tp = topo(filePath)
    
    print("创建容器!\r")
    os.system("sudo python3 {}/create_docker.py".format(filePath))

    # 是否需要生成配置文件，如果需要，执行命令时就输入参数。如python3 run.py 1
    # if len(sys.argv) > 0:
    print("控制通道路由生成，并且写成脚本!\r")
    gen_route2sh(tp)
    print("时间片链路修改脚本生成!\r")
    gen_diff_links2sh(tp)

    print("配置文件复制进入容器当中!\r")
    cp_sh2docker(tp)

    print("第0个时间片的拓扑链路生成，并且放入对应的docker容器\r")
    os.system("sudo {}/config/links_shell/links_init_slot0.sh".format(tp.filePath))
    print(str(time.time() - start)+'\r')

    print("在所有的ovs容器中启动对应的ovs交换机，将端口绑定到ovs交换机上!\r")
    with ThreadPoolExecutor(max_workers=tp.num_sw) as pool:
        all_task = []
        print("每个sw容器初始化执行!\r")
        for sw_no in tp.data_topos[0]:   
            all_task.append(pool.submit(os.system, "sudo docker exec -it s{} /bin/bash /home/config/links_shell/s{}_init_slot0.sh".format(sw_no, sw_no)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()

        print("加载第0个时间片的默认控制通道路由!\r")
        for sw_no in tp.data_topos[0]:  # ct-db的路由读取
            all_task.append(pool.submit(os.system, "sudo docker exec -it s{} ovs-ofctl add-flows s{} /home/config/sw_route_file/fl_ct2db_s{}_slot0".format(sw_no, sw_no, sw_no)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()
        for sw_no in tp.data_topos[0]:  # db-db的路由读取
            all_task.append(pool.submit(os.system, "sudo docker exec -it s{} ovs-ofctl add-flows s{} /home/config/sw_route_file/fl_db2db_s{}_slot0".format(sw_no, sw_no, sw_no)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()
        print("数据库的接口ip配置等!\r")
        for db_no in tp.db_data:        # 数据库的接口ip配置等
            all_task.append(pool.submit(os.system,"sudo {}/config/db_conf/db_init.sh {} ".format(tp.filePath, db_no)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()

        print("启动所有的数据库及其代理!\r")
        for db_no in tp.db_data:
            all_task.append(pool.submit(os.system,"sudo docker exec -it db{} /bin/bash -c \"/home/config/db_conf/db_run.sh start {} {}\"".format(db_no, db_no, 0)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()
        for db_no in tp.db_data:
            all_task.append(pool.submit(os.system,"sudo docker exec db{} /bin/bash -c \"stdbuf -oL nohup /home/monitor_new 192.168.68.{} > /home/db.log 2>&1 &\"".format(db_no, db_no+1)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()

        print("启动所有的控制器，并且连接到所属的数据库，同时本地的ovs交换机连接到本地的控制器!\r")
        for sw_no in tp.data_topos[0]:  
            all_task.append(pool.submit(os.system,"sudo docker exec -it s{s} /bin/bash -c \"/usr/src/openmul/mul.sh start mulhello > /dev/null;\""\
                .format(s=sw_no)))
        wait(all_task, return_when=ALL_COMPLETED)
        all_task.clear()
        time.sleep(5)   # 由于仿真运行时延的原因，需要等几秒
        for sw_no in tp.data_topos[0]:  
            all_task.append(pool.submit(os.system,"sudo docker exec -it s{s} /bin/bash -c \"echo {slot} > /dev/udp/192.168.66.{ip}/12000\";sudo docker exec s{s} ovs-vsctl set-controller s{s} tcp:192.168.66.{ip}:6653 -- set bridge s{s} other_config:enable-flush=false;sudo docker exec s{s} ovs-vsctl set controller s{s} connection-mode=out-of-band"\
                .format(s=sw_no, ip=sw_no+1, slot=0)))
        wait(all_task, return_when=ALL_COMPLETED)

    print("启动监听指令程序!\r")
    print(str(time.time() - start)+'\r')
    # ctrl = controller(tp)