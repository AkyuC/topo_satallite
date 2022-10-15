import os
import sys

if __name__ == "__main__":
    # sys.argv[0]表示文件名，sys.argv[1]表示db编号

    os.system("sudo docker exec -it db{db} cat /home/config/db_conf/db{db}.log".format(db=sys.argv[1]))

