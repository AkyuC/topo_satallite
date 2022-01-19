import os
import sys

if __name__ == "__main__":
    # sys.argv[0]表示文件名，sys.argv[3]表示sw编号，sys.argv[1]表示源地址（66.1），sys.argv[2]表示目的地址（68.17），sys.argv[4]表示协议号，默认ip（1），arp（2）

    if len(sys.argv) == 4:
        os.system("sudo docker exec -it s{} ovs-ofctl dump-flows s{} | grep 192.168.{},nw_dst=192.168.{}".format(sys.argv[3], sys.argv[3], sys.argv[1], sys.argv[2]))
    elif int(sys.argv[4]) == 1:
        os.system("sudo docker exec -it s{} ovs-ofctl dump-flows s{} | grep 192.168.{},nw_dst=192.168.{}".format(sys.argv[3], sys.argv[3], sys.argv[1], sys.argv[2]))
    else:
        os.system("sudo docker exec -it s{} ovs-ofctl dump-flows s{} | grep 192.168.{},arp_tpa=192.168.{}".format(sys.argv[3], sys.argv[3], sys.argv[1], sys.argv[2]))

