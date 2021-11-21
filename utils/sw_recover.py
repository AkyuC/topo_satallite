from topo.topo import topo
import os

def sw_rec_create_veth(sw_no, slot_no, sw_fail: set, tp: topo):
    # 添加veth-pair
    filename = tp.filePath + "/config/sw_recover/sw{}_rec_crt_vp.sh"
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
            if sw_adj not in sw_fail:
                file.write("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n"\
                    .format(sw_adj, sw_adj, p2, p2, sw_no+1000))
                file.write("sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw_adj, p2, int(tp.data_topos[slot_no][sw_no][sw_adj]*1000)))
    os.system("sudo chmod +x {f}; sudo {f}".format(f=filename))

def sw_rec_add_veth(sw_no, slot_no, tp: topo):
    # 将veth-pair绑定到ovs交换机上面
    filename = tp.filePath + "/config/sw_recover/sw{}_rec_add_ovs.sh"
    with open(filename, 'w+') as file:
        for sw_adj in tp.data_topos[slot_no][sw_no]:
            p = "s{}-s{}".format(sw_no,sw_adj)
            file.write("sudo docker exec -it s{} ovs-vsctl add-port s{} {} -- set interface {} ofport_request={} > /dev/null\n"\
                .format(sw_no, sw_no, p, p, sw_no+1000))
            file.write("sudo docker exec -it s{} tc qdisc add dev {} root netem delay {}ms > /dev/null\n".format(sw_no, p, int(tp.data_topos[slot_no][sw_no][sw_adj]*1000)))
    os.system("sudo chmod +x {f}; sudo {f}".format(f=filename))