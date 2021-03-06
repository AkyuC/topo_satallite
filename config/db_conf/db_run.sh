#!/bin/sh
#需要输入参数，即db的id, 运行的时间片

id=$2
slot_no=$3
ip_recover=$4
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
DYNOMITE_EXEC=/home/dynomite/src/dynomite
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
    ps -ef | grep redis-server | grep -v grep | cut -c 8-16 | xargs kill -9
}

stop_dynomite(){
    ps -ef | grep dynomite | grep -v grep | cut -c 8-16 | xargs kill -9
}

start_dynomite(){
    $DYNOMITE_EXEC -c $DYNOMITE_CONF -d --output=$DYNOMITE_LOG
}

start_monitor(){
if [ $id -eq 13 ]
    then
            sleep 1s
            /home/config/db_conf/init_map $slot_no $REDIS_IP > /dev/null 
    fi
}

stop_monitor(){
    ps -ef | grep monitor_new | grep -v grep | cut -c 8-16 | xargs kill -9
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
}

redis_recover(){
	$CLIREDIS_EXEC -h $REDIS_IP -p $REDISPORT slaveof 192.168.68.$ip_recover 6379
	sleep 5s
	$CLIREDIS_EXEC -h $REDIS_IP -p $REDISPORT slaveof NO ONE
}
 
case "$1" in
    start)
        start_redis
        start_dynomite
        ;;
    stop)
        stop_monitor
        stop_dynomite
        stop_redis
        ;;
    restart)
        stop_monitor
        stop_dynomite
        stop_redis
        start_redis
        start_dynomite
        ;;
    redis_recover)
        redis_recover
        ;;
    *) echo "unknown command"
        ;;
esac
