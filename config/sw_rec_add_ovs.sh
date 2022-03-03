id=$1
ip=`expr $id + 1`
dpid=`expr $id + 1000`

if [ $3 -eq 1 ]
then
    chmod +x /home/ovs_open.sh; ./home/ovs_open.sh > /dev/null
fi

ovs-vsctl add-br s$id -- set bridge s$id protocols=OpenFlow10,OpenFlow13 other_config:datapath-id=$(printf "%016x" $dpid)
ovs-vsctl set bridge s$id other_config:datapath-id=$(printf "%016x" $dpid)
ovs-vsctl set bridge s$id other_config:enable-flush=false
ovs-vsctl set-fail-mode s$id secure
ifconfig s$id 192.168.66.$ip netmask 255.255.0.0 up
route add default dev s$id
ovs-vsctl set-controller s$id tcp:192.168.10.1:6653 -- set bridge s$id other_config:enable-flush=false
ovs-vsctl set bridge s$id other_config:disable-in-band=false
ovs-vsctl set controller s$id connection-mode=out-of-band
ovs-ofctl add-flow s$id "table=0,priority=50 action=resubmit(,1)"
ovs-ofctl add-flow s$id "table=1,priority=10,ip action=drop"
ovs-ofctl add-flow s$id "table=1,priority=10,arp action=drop"
ovs-ofctl add-flow s$id "table=0,priority=100,ip,nw_dst=192.168.66.$ip action=output:LOCAL"
ovs-ofctl add-flow s$id "table=0,priority=100,arp,nw_dst=192.168.66.$ip action=output:LOCAL"
ovs-ofctl add-flow s$id "table=0,priority=100,ip,nw_dst=192.168.10.1 action=drop"
ovs-ofctl add-flow s$id "table=0,priority=100,arp,nw_dst=192.168.10.1 action=drop"
nohup iperf -s -u > /dev/null 2>&1 &
# if [ $2 -eq 1 ]
# then
#     dbid=`expr $id + 2000`
#     ovs-ofctl add-flow s$id "table=0,priority=100,ip,nw_dst=192.168.68.$ip action=output:$dbid"
#     ovs-ofctl add-flow s$id "table=0,priority=100,arp,nw_dst=192.168.68.$ip action=output:$dbid"
# fi
