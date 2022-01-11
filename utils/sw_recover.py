from topo.topo import topo
import os

def sw_rec_ovs(sw_no, is_delsw, is_db):
    # 恢复容器当中的ovs
    command = ""
    reconn_ovs = 1
    if(is_delsw is True):
        command += "sudo docker exec -it s{} /bin/bash -c \"/usr/src/openmul/mul.sh stop > /dev/null;ovs-vsctl del-br s{};\";".format(sw_no, sw_no)
        reconn_ovs = 0
    if(is_db is True):
        command +="sudo docker exec -it s{} /bin/bash -c \"/home/config/sw_rec_add_ovs.sh {} {} {} > /dev/null\";".format(sw_no, sw_no, 1, reconn_ovs)
    else:
        command += "sudo docker exec -it s{} /bin/bash -c \"/home/config/sw_rec_add_ovs.sh {} {} {} > /dev/null\";".format(sw_no, sw_no, 0, reconn_ovs)
    os.system(command)

def sw_rec_create_veth(sw_no, slot_no, sw_fail: set, tp: topo):
    # 添加veth-pair
    filename = tp.filePath + "/config/sw_recover/sw{}_rec_crt_vp.sh".format(sw_no)
    with open(filename, 'w+') as file:
        for sw_adj in tp.data_topos[slot_no][sw_no]:
            if sw_adj in sw_fail and sw_no < sw_adj:
                continue
            p1 = "s{}-s{}".format(sw_no,sw_adj)
            p2 = "s{}-s{}".format(sw_adj,sw_no)
            file.write("sudo ip link add {} type veth peer name {}\n".format(p1, p2))
            file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up > /dev/null\n"\
                .format(p1, p1, sw_no))
            file.write("sudo ip link set dev {} name {} netns $(sudo docker inspect -f '{{{{.State.Pid}}}}' s{}) up > /dev/null\n"\
                .format(p2, p2, sw_adj))
            file.write("sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw_no, p1, int(tp.data_topos[slot_no][sw_no][sw_adj]*1000)))
            if sw_adj not in sw_fail:
                file.write("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n"\
                    .format(sw_adj, sw_adj, p2, p2, sw_no+1000))
                file.write("sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw_adj, p2, int(tp.data_topos[slot_no][sw_no][sw_adj]*1000)))
    os.system("sudo chmod +x {f}; sudo {f}".format(f=filename))

def sw_rec_add_veth(sw_no, slot_no, tp: topo):
    # 将veth-pair绑定到ovs交换机上面
    filename = tp.filePath + "/config/sw_recover/sw{}_rec_add_ovs_port.sh".format(sw_no)
    with open(filename, 'w+') as file:
        for sw_adj in tp.data_topos[slot_no][sw_no]:
            p = "s{}-s{}".format(sw_no, sw_adj)
            file.write("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n"\
                .format(sw_no, sw_no, p, p, sw_adj+1000))
            # file.write("sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw_no, p, int(tp.data_topos[slot_no][sw_no][sw_adj]*1000)))
        if sw_no in tp.db_data:
            p = "s{}-db{}".format(sw_no, sw_no)
            file.write("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n"\
                .format(sw_no, sw_no, p, p, sw_no+2000))
    os.system("sudo chmod +x {f}; sudo {f}".format(f=filename))