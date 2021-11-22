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
        for sw_no in tp.data_topos[0]:
        # 控制器根据时间片连接数据库的配置文件复制
            all_task.append(pool.submit(__cp_a_file2docker_sw, sw_no, "{}/config/ctrl_conn_db/ctrl_{}".format(tp.filePath, sw_no), "ctrl2db"))
        wait(all_task, return_when=ALL_COMPLETED)