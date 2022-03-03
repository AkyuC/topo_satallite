import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from topo.topo import topo
from topo.route import route


def __a_db2db_rt2sh(sw_no, filename, rt:list):
    # 将一个sw上面的有关db-db的流表项写成shell文件
    with open(filename, 'w+') as file:
        for iu in rt:
            if len(iu) == 3:
                file.write("table=0,priority=100,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{},action=output:{}\n"\
                    .format(iu[0]+1, iu[1]+1, iu[2]))
                file.write("table=0,priority=100,arp,arp_spa=192.168.68.{},arp_tpa=192.168.68.{},action=output:{}\n"\
                    .format(iu[0]+1, iu[1]+1, iu[2]))
            elif iu[0] == sw_no:
                file.write("table=0,priority=100,ip,nw_src=192.168.68.{},nw_dst=192.168.68.{},action=output:{},{}\n"\
                    .format(iu[0]+1, iu[1]+1, iu[2], iu[3]))
                file.write("table=0,priority=100,arp,arp_spa=192.168.68.{},arp_tpa=192.168.68.{},action=output:{},{}\n"\
                    .format(iu[0]+1, iu[1]+1, iu[2], iu[3]))
            else:
                file.write("table=0,priority=100,in_port={},ip,nw_src=192.168.68.{},nw_dst=192.168.68.{},action=output:{}\n"\
                    .format(iu[3], iu[0]+1, iu[1]+1, iu[2]))
                file.write("table=0,priority=100,in_port={},arp,arp_spa=192.168.68.{},arp_tpa=192.168.68.{},action=output:{}\n"\
                    .format(iu[3], iu[0]+1, iu[1]+1, iu[2]))

def __a_sw2db_rt2sh(filename, rt:list):
    # 将一个sw上面的有关ct-db的流表项写成shell文件
    with open(filename, 'w+') as file:
        for iu in rt:
            if iu[0] == 1:
                file.write("table=0,priority=100,ip,nw_src=192.168.66.{},nw_dst=192.168.68.{},action=output:{}\n"\
                    .format(iu[1]+1, iu[2]+1, iu[3]))
                file.write("table=0,priority=100,arp,arp_spa=192.168.66.{},arp_tpa=192.168.68.{},action=output:{}\n"\
                    .format(iu[1]+1, iu[2]+1, iu[3]))
            else:
                file.write("table=0,priority=100,ip,nw_src=192.168.68.{},nw_dst=192.168.66.{},action=output:{}\n"\
                    .format(iu[1]+1, iu[2]+1, iu[3]))
                file.write("table=0,priority=100,arp,arp_spa=192.168.68.{},arp_tpa=192.168.66.{},action=output:{}\n"\
                    .format(iu[1]+1, iu[2]+1, iu[3]))

def gen_route2sh(tp: topo):
    # 所有时间片，每个控制器到所有分布式数据库的控制通道路由，以及数据库之间的路由，并且复制到对于的容器当中
    # 脚本的文件夹生成
    if not os.path.exists(tp.filePath + "/config/sw_route_file"):
        os.makedirs(tp.filePath + "/config/sw_route_file")
    
    with ThreadPoolExecutor(max_workers=32) as pool:
        all_task = []
        for slot_no in tp.data_topos:
            # 生成脚本
            # 数据库和数据库之间
            db2db_rt = route.load_db2db(tp.num_sw, "{}/config/route_d2d/d2d_{}".format(tp.filePath, slot_no))
            # db-db的控制通道路由生成shell脚本
            all_task.clear()
            for sw_no in tp.data_topos[0]:
                all_task.append(pool.submit(__a_db2db_rt2sh, sw_no, "{}/config/sw_route_file/fl_db2db_s{}_slot{}".format(tp.filePath, sw_no, slot_no), db2db_rt[sw_no]))
            wait(all_task, return_when=ALL_COMPLETED)
            
            # 控制器和数据库之间
            sw2db_rt = route.load_ctrl2db(tp.num_sw, "{}/config/route_c2d/c2d_{}".format(tp.filePath, slot_no))
            # ct-db的控制通道路由生成shell脚本
            all_task.clear()
            for sw_no in tp.data_topos[0]:
                all_task.append(pool.submit(__a_sw2db_rt2sh, "{}/config/sw_route_file/fl_ct2db_s{}_slot{}".format(tp.filePath, sw_no, slot_no), sw2db_rt[sw_no]))
            wait(all_task, return_when=ALL_COMPLETED)

def __a_slot_diff_links2sh(slot_no, path, links:list):
    # 将一个时间片的链路修改写成shell文件
    filename = path + "links_add_slot{}.sh".format(slot_no)
    with open(filename, 'w+') as file:
        for sw_no in links:
            for link in links[sw_no]: # ubuntu宿主机创建veth-pair
                if link[0] == 1:    # 先把需要添加的链路先放入docker容器当中
                    if link[1]>link[2]:
                        p1 = "s{}-s{}".format(link[1],link[2])
                        p2 = "s{}-s{}".format(link[2],link[1])
                        file.write("sudo ip link add {} type veth peer name {} > /dev/null\n".format(p1, p2))
                        file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up > /dev/null\n"\
                            .format(p1, p1, link[1]))
                        file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up > /dev/null\n"\
                            .format(p2, p2, link[2]))
                        # file.write("sudo docker exec -it s{} ip link set {} up > /dev/null\n".format(link[1], p1))
                        # file.write("sudo docker exec -it s{} ip link set {} up > /dev/null\n".format(link[2], p2))
    
    os.system("sudo chmod +x {}".format(filename))  # 修改权限

    for sw_no in links:
        filename = path + "s{}_links_change_slot{}.sh".format(sw_no, slot_no)
        with open(filename, 'w+') as file:
            for link in links[sw_no]:  # 修改容器内部的链路连接到ovs交换机上面
                p = "s{}-s{}".format(link[1],link[2])
                if link[0] == 0:   # 修改链路时延，因为保存了两遍，所以只需要写一侧，下面也是
                    file.write("tc qdisc change dev {} root netem delay {}ms > /dev/null\n".\
                        format(p, int(link[3]*1000)))
                elif link[0] == -1: # 删除链路
                    file.write("ovs-vsctl del-port s{} {} > /dev/null;\n".format(link[1], p))
                    if link[1]>link[2]: # veth-pair删除一边就能把另一边也删除
                        file.write("tc qdisc del dev {} root > /dev/null; ip link delete {} > /dev/null\n".format(p, p))
                else:   # 将veth-pair绑到ovs上，并且设置端口号，这里的端口号连接那个卫星交换机，就设置为1000+id，如s1连接s2的端口号就是1002，s2连接s1的端口就是1001，本地局部不一样就可以
                    file.write("ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n"\
                        .format(link[1], p, p, link[2]+1000))
                    file.write("tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(p, int(link[3]*1000)))
    
        os.system("sudo chmod +x {}".format(filename))  # 修改权限

def __a_sw_init_slot2sh(sw_no, filename, sw_adj:dict, is_db=False):
    # 将一个sw初始化写成shell脚本
    with open(filename, 'w+') as file:
        # file.write("ip route flush table main\n".format(sw_no)) # 清空linux的路由表
        file.write("chmod +x /home/ovs_open.sh; ./home/ovs_open.sh > /dev/null\n")  # 启动ovs
        file.write("ovs-vsctl add-br s{} -- set bridge s{} protocols=OpenFlow10,OpenFlow13 other_config:datapath-id={}\n".format(sw_no, sw_no, sw_no+1000))  # 创建sw
        file.write("ovs-vsctl set bridge s{} other_config:datapath-id={:016X}\n".format(sw_no,sw_no+1000))  # 设置dpid等等
        file.write("ovs-vsctl set bridge s{} other_config:enable-flush=false\n".format(sw_no))
        file.write("ovs-vsctl set-fail-mode s{} secure\n".format(sw_no))
        file.write("ifconfig s{} 192.168.66.{} netmask 255.255.0.0 up\n".format(sw_no, sw_no+1))  # ip设置
        file.write("route add default dev s{}\n".format(sw_no)) # 默认路由设置
        # 连接一个不存在的控制器，使得sw的模式改为流表匹配模式
        file.write("ovs-vsctl set-controller s{} tcp:192.168.10.1:6653 -- set bridge s{} other_config:enable-flush=false\n".format(sw_no, sw_no))
        file.write("ovs-vsctl set bridge s{} other_config:disable-in-band=false\n".format(sw_no))   # 设置连接控制器的模式
        file.write("ovs-vsctl set controller s{} connection-mode=out-of-band\n".format(sw_no))
        # 本地流表设置
        file.write("ovs-ofctl add-flow s{} \"table=0,priority=50 action=resubmit(,1)\"\n".format(sw_no))
        file.write("ovs-ofctl add-flow s{} \"table=1,priority=10,ip action=drop\"\n".format(sw_no))
        file.write("ovs-ofctl add-flow s{} \"table=1,priority=10,arp action=drop\"\n".format(sw_no))
        file.write("ovs-ofctl add-flow s{} \"table=0,priority=100,ip,nw_dst=192.168.66.{} action=output:LOCAL\"\n".format(sw_no, sw_no+1))
        file.write("ovs-ofctl add-flow s{} \"table=0,priority=100,arp,nw_dst=192.168.66.{} action=output:LOCAL\"\n".format(sw_no, sw_no+1))
        if(is_db):
            file.write("ovs-ofctl add-flow s{} \"table=0,priority=100,ip,nw_dst=192.168.68.{} action=output:{}\"\n".format(sw_no, sw_no+1, sw_no+2000))
            file.write("ovs-ofctl add-flow s{} \"table=0,priority=100,arp,nw_dst=192.168.68.{} action=output:{}\"\n".format(sw_no, sw_no+1, sw_no+2000))
        file.write("ovs-ofctl add-flow s{} \"table=0,priority=100,ip,nw_dst=192.168.10.1 action=drop\"\n".format(sw_no))
        file.write("ovs-ofctl add-flow s{} \"table=0,priority=100,arp,nw_dst=192.168.10.1 action=drop\"\n".format(sw_no))
        file.write("nohup iperf -s -u > /dev/null 2>&1 &\n")
        # 将slot0的链接端口绑定到sw上
        for sw_adj_no in sw_adj:
            p = "s{}-s{}".format(sw_no, sw_adj_no)
            file.write("ovs-vsctl add-port s{} {} -- set interface {} ofport_request={}\n".format(sw_no, p, p, sw_adj_no+1000))
            file.write("tc qdisc add dev {} root netem delay {}ms\n".format(p,int(sw_adj[sw_adj_no]*1000)))
            file.write("ip link set dev {} up\n".format(p))

    os.system("sudo chmod +x {}".format(filename))  # 修改权限
    os.system("sudo cp {} {}".format(filename, filename + ".back"))  # 保存一份备份，用于拓扑恢复
        
def gen_diff_links2sh(tp: topo):
    # 所有时间片切换链路的脚本生成
    # 脚本的文件夹生成
    if not os.path.exists(tp.filePath + "/config/links_shell"):
        os.makedirs(tp.filePath + "/config/links_shell")
    
    # 第0个时间片的链路初始化脚本生成
    # veth-pair生成，并且放入对应的容器当中
    with open(tp.filePath + "/config/links_shell/links_init_slot0.sh", 'w+') as file:
        for sw1 in tp.data_topos[0]:
            for sw2 in tp.data_topos[0][sw1]:
                if sw1 > sw2:
                    p1 = "s{}-s{}".format(sw1,sw2)
                    p2 = "s{}-s{}".format(sw2,sw1)
                    file.write("sudo ip link add {} type veth peer name {} > /dev/null\n".format(p1, p2))
                    file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up\n".format(p1, p1, sw1))
                    file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up\n".format(p2, p2, sw2))
                    # file.write("sudo docker exec -it s{} ip link set {} up > /dev/null\n".format(sw1, p1))
                    # file.write("sudo docker exec -it s{} ip link set {} up > /dev/null\n".format(sw2, p2))
            
    os.system("sudo chmod +x {}".format(tp.filePath + "/config/links_shell/links_init_slot0.sh"))  # 修改权限
    # sw的ovs初始化，创建ovs交换机等等
    with ThreadPoolExecutor(max_workers=32) as pool:
        all_task = []
        for sw_no in tp.data_topos[0]:   
            if(sw_no in tp.db_data):
                all_task.append(pool.submit(__a_sw_init_slot2sh, sw_no, "{}/config/links_shell/s{}_init_slot0.sh".format(tp.filePath, sw_no), tp.data_topos[0][sw_no], True))
            else:
                all_task.append(pool.submit(__a_sw_init_slot2sh, sw_no, "{}/config/links_shell/s{}_init_slot0.sh".format(tp.filePath, sw_no), tp.data_topos[0][sw_no], False))
        wait(all_task, return_when=ALL_COMPLETED)

    # 时间片切换的链路修改
        all_task.clear()
        for slot_no in tp.data_topos:
            all_task.append(pool.submit(__a_slot_diff_links2sh, slot_no, tp.filePath + "/config/links_shell/", tp.diff_topos[slot_no]))
        wait(all_task, return_when=ALL_COMPLETED)