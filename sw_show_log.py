import os
import sys

if __name__ == "__main__":
    # sys.argv[0]表示文件名，sys.argv[1]表示sw编号

    os.system("sudo docker exec -it s{} cat /var/log/mulhello.log".format(sys.argv[1]))

