import os

if __name__ == "__main__":
    db_list=[13,16,31,46,50,54]

    for i in range(6):
        for j in range(i+1,6):
            print("数据库{} ping 数据库{}".format(db_list[i], db_list[j]))
            os.system("sudo docker exec -it db{} ping -c 2 192.168.68.{}".format(db_list[i], db_list[j]+1))

