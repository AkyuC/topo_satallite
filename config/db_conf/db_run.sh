#!/bin/sh
#需要输入参数，即db的id, 运行的时间片

id=$2
slot_no=$3
ip=`expr $id + 1`

#redis
REDISPORT=6379
#服务端所处位置
REDIS_EXEC=/usr/bin/redis-server
#客户端位置
CLIREDIS_EXEC=/usr/bin/redis-cli
#redis的PID文件位置，需要修改
REDIS_PIDFILE=/var/run/redis-server.pid
#redis的配置文件位置，需将${REDIS_REDISPORT}修改为文件名
REDIS_CONF="/home/config/db_conf/redis_$id.conf"

REDIS_IP="192.168.68.$ip"

#dynomite
#
DYNOMITE_EXEC=/usr/sbin/dynomite
#
DYNOMITE_CONF="/home/config/db_conf/dyno_$id.yml"
#
DYNOMITE_LOG="/home/config/db_conf/dyno_$id.log"

start_redis(){
    cp /home/config/db_conf/dump.rdb.back /var/lib/redis/dump.rdb
    if [ -f $REDIS_PIDFILE ]
    then
            echo "$REDIS_PIDFILE exists, process is already running or crashed"
    else
            $REDIS_EXEC $REDIS_CONF
    fi
}

stop_redis(){
if [ ! -f $PIDFILE ]
    then
            echo "$PIDFILE does not exist, process is not running"
    else
            PID=$(cat $REDIS_PIDFILE)
            $CLIREDIS_EXEC -h $REDIS_IP -p $REDISPORT shutdown
            while [ -x /proc/${PID} ]
            do
                sleep 1
            done
    fi
    killall -9 redis-cli
}

stop_dynomite(){
    killall -9 dynomite
}

start_dynomite(){
    $DYNOMITE_EXEC -c $DYNOMITE_CONF -d --output=$DYNOMITE_LOG
}

start_monitor(){
    sleep 1s
    /home/config/db_conf/init_map $slot_no $REDIS_IP > /dev/null 
}

stop_monitor(){
    killall -9 monitor_new
}

restart_redis(){
    if [ ! -f $REDIS_PIDFILE ]
    then
            cp /home/config/db_conf/dump.rdb.back /var/lib/redis/dump.rdb
            $REDIS_EXEC $REDIS_CONF 
    else
            PID=$(cat $REDIS_PIDFILE)
            $CLIREDIS_EXEC -h $REDIS_IP -p $REDIS_REDISPORT shutdown
            while [ -x /proc/${PID} ]
            do
                sleep 1
            done
            cp /home/config/db_conf/dump.rdb.back /var/lib/redis/dump.rdb
            $REDIS_EXEC $REDIS_CONF             
    fi
    killall -9 redis-cli
}
 
case "$1" in
    start)
        start_redis
        start_dynomite
        start_monitor
        ;;
    stop)
        stop_monitor
        stop_dynomite
        stop_redis
        ;;
    restart)
        stop_monitor
        stop_dynomite
        restart_redis
        start_dynomite
        start_monitor
        ;;
    *) echo "unknown command"
        ;;
esac
