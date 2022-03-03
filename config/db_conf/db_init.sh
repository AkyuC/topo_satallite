#需要输入一个参数，即db的id

if [ ! -n "$1" ] ;then
    echo "请输入数据库id"
    exit
fi

# 设置变量
id=$1
ip=`expr $id + 1`
p1=db$id-s$id
p2=s$id-db$id
sport=`expr $id + 2000`

# ip和route设置
sudo ip link add $p1 type veth peer name $p2 > /dev/null
sudo ip link set dev $p2 name $p2 netns $(sudo docker inspect -f '{{.State.Pid}}' s$id) up
sudo ip link set dev $p1 name $p1 netns $(sudo docker inspect -f '{{.State.Pid}}' db$id) up

sudo docker exec -it db$id ifconfig $p1 192.168.68.$ip netmask 255.255.0.0 up
sudo docker exec -it db$id route add default dev $p1

sudo docker exec -it s$id ovs-vsctl add-port s$id $p2 -- set interface $p2 ofport_request=$sport > /dev/null
sudo docker exec -it s$id ovs-ofctl add-flow s$id "table=0,priority=100,ip,nw_dst=192.168.68.$ip action=output:$sport"
sudo docker exec -it s$id ovs-ofctl add-flow s$id "table=0,priority=100,arp,nw_dst=192.168.68.$ip action=output:$sport"
