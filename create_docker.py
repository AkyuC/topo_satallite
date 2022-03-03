import os

if __name__ == '__main__' :
    #获取当前文件路径，读取配置文件需要
    filePath = os.getcwd()

    sw_num = 0
    with open(file=filePath + "/config/timeslot/test_0") as file:
        line = file.readline().strip("\n")
        sw_num = int(line) # 获取卫星交换机的数量
    for index in range(sw_num):
        # docker import --change 'CMD ["/usr/bin/supervisord"]' satellite.tar satellite
        os.system("sudo docker create -it --name=s{} --net=none --privileged -v /etc/localtime:/etc/localtime:ro -v {}/config:/home/config -v /home/openmul/openmul:/usr/src/openmul satellite /bin/bash > /dev/null".format(index, filePath))
        os.system("sudo docker start s{} > /dev/null".format(index))

    with open(file=filePath + "/config/db_conf/db_deploy") as file:
        # docker import --change 'CMD ["/usr/bin/supervisord"]' database.tar database
        lines = file.read().splitlines()
        db_num = int(lines[0].strip().split()[0]) # 获取分布式数据库的数量
        db_data = lines[1].strip().split()   # 获取分布式数据库的位置
        db_data = list(map(int, db_data))
        for db in db_data:
            os.system("sudo docker create -it --name=db{} --net=none --privileged -v /etc/localtime:/etc/localtime:ro -v {}/config:/home/config -v /home/openmul/dynomite:/home/dynomite database /bin/bash > /dev/null".format(db, filePath))
            os.system("sudo docker start db{} > /dev/null".format(db))