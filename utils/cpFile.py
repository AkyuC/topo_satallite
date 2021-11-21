import os
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from topo.topo import topo

def __cp_a_file2docker_db(sw_no, filename, name=None):
    # 复制一个文件去对应的容器的/home目录下
    if name is None:
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^db{}$\"):/home\n".format(filename, sw_no))
    else:
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^db{}$\"):/home/{}\n".format(filename, sw_no, name))

def __cp_a_file2docker_sw(sw_no, filename, name=None):
    # 复制一个文件去对应的容器的/home目录下
    if name is None:
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home\n".format(filename, sw_no))
    else:
        os.system("sudo docker cp {} $(sudo docker ps -aqf\"name=^s{}$\"):/home/{}\n".format(filename, sw_no, name))

def cp_sh2docker(tp: topo):
    # 将脚本复制到对应容器的/home目录下
    with ThreadPoolExecutor(max_workers=tp.num_sw) as pool:
        all_task = []
        for slot_no in tp.data_topos:
            for sw_no in tp.data_topos[slot_no]:   
                # db-db的路由脚本文件复制
                all_task.append(pool.submit(__cp_a_file2docker_sw, sw_no, "{}/config/sw_route_file/fl_db2db_s{}_slot{}".format(tp.filePath, sw_no, slot_no)))
                # ctrl-db的路由脚本文件复制
                all_task.append(pool.submit(__cp_a_file2docker_sw, sw_no, "{}/config/sw_route_file/fl_ct2db_s{}_slot{}".format(tp.filePath, sw_no, slot_no)))
                # links修改的脚本复制
                all_task.append(pool.submit(__cp_a_file2docker_sw, sw_no, "{}/config/links_shell/s{}_links_change_slot{}.sh".format(tp.filePath, sw_no, slot_no)))
        for sw_no in tp.data_topos[slot_no]:    
        # sw初始化的脚本文件复制
            all_task.append(pool.submit(__cp_a_file2docker_sw, sw_no, "{}/config/links_shell/s{}_init_slot0.sh".format(tp.filePath, sw_no)))
        # 控制器根据时间片连接数据库的配置文件复制
            all_task.append(pool.submit(__cp_a_file2docker_sw, sw_no, "{}/config/ctrl_conn_db/ctrl_{}".format(tp.filePath, sw_no), "ctrl2db"))
        # 数据库的启动配置文件复制
        for db_no in tp.db_data:
            all_task.append(pool.submit(__cp_a_file2docker_db, db_no, "{}/config/db_conf/monitor_new".format(tp.filePath)))
            all_task.append(pool.submit(__cp_a_file2docker_db, db_no, "{}/config/db_conf/init_map".format(tp.filePath))) 
            all_task.append(pool.submit(__cp_a_file2docker_db, db_no, "{}/config/db_conf/db_run.sh".format(tp.filePath, db_no)))  
            all_task.append(pool.submit(__cp_a_file2docker_db, db_no, "{}/config/db_conf/dump.rdb.back".format(tp.filePath, db_no)))            
            all_task.append(pool.submit(__cp_a_file2docker_db, db_no, "{}/config/db_conf/dyno_{}.yml".format(tp.filePath, db_no)))
            all_task.append(pool.submit(__cp_a_file2docker_db, db_no, "{}/config/db_conf/redis_{}.conf".format(tp.filePath, db_no)))
        wait(all_task, return_when=ALL_COMPLETED)