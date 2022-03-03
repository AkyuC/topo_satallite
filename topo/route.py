class route:    
    @staticmethod
    def load_db2db(sw_num, filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()   # 储存每个交换机上面的db-db的流表条目
        for sw_no in range(sw_num): # 初始化
            data[sw_no] = list()
        with open(file=filename) as file:   # 文件读取
            lines = file.read().splitlines()
            for line in lines:
                line_list = line.strip().split()
                db1 = int(line_list[0])
                if len(line_list)==1:   # 标识行
                    continue
                db2 = int(line_list[1])
                for i in range(len(line_list)-2):   # 条目读取
                    port_add = False
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw*1000
                    if i == 0:
                        for f in data[sw]:
                            if f[0] == db1 and f[1] == db2:
                                f.append(port+1000)
                                port_add = True
                                break
                        if not port_add:
                            data[sw].append([db1, db2, port+1000])  # 1000为端口的偏移值
                    else:
                        data[sw].append([db1, db2, port+1000, int(int(line_list[i+1])/1000)+1000])  # 1000为端口的偏移值
        return data
    
    def load_ctrl2db(sw_num, filename:str):
        # 从文件当中加载一个时间片的默认路由信息
        data = dict()   # 储存每个交换机上面的db-db的流表条目
        for sw_no in range(sw_num): # 初始化
            data[sw_no] = list()
        with open(file=filename) as file:   # 文件读取
            lines = file.read().splitlines()
            for index in range(len(lines)):
                line = lines[index]
                line_list = line.strip().split()
                node1 = int(line_list[0])
                node2 = int(line_list[1])
                for i in range(len(line_list)-2): # 条目读取
                    flow = int(line_list[i+2])
                    sw = int(flow/1000)
                    port = flow - sw*1000
                    if index%2 == 0:
                        data[sw].append((-1, node1, node2, port+1000))   # 由于ip是不一样的，所以这里使用了1表示ctrl到db的路由表项，-1表示ctrl到sw的路由表项
                    else:
                        data[sw].append((1, node1, node2, port+1000))   # 由于ip是不一样的，所以这里使用了1表示ctrl到db的路由表项，-1表示db到ctrl的路由表项
        return data