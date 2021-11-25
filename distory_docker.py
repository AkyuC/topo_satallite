import os


if __name__ == '__main__' :
    #获取当前文件路径，读取配置文件需要
    os.system("sudo docker stop $(sudo docker ps -a -q)")
    os.system("sudo docker rm $(sudo docker ps -a -q)")