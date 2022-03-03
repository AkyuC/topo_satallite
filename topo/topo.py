import os


class topo:
    def __init__(self, filePath:str) -> None:
        self.num_slot = 0   # 时间片的个数
        self.num_sw = 0 # 卫星交换机的个数
        self.num_db = 0 # 分布式数据库的个数
        self.db_data = list() # 分布式数据库位置
        self.data_topos = dict() # 所有时间片的数据
        self.diff_topos = dict() # 存储不同时间片之间需要改变的链路信息
        self.filePath = filePath # 获取当前的文件路径
        self.read_topo_db() # 从文件当中读取数据库位置
        self.read_topo()    # 从文件当中读取拓扑
        self.diff_links()   # 获取时间片变换的链路

    def read_topo_db(self):
        # 获取分布式数据库位置
        with open(self.filePath + "/config/db_conf/db_deploy") as file:
            lines = file.read().splitlines()
            self.num_db = int(lines[0].strip().split()[0]) # 获取分布式数据库的数量
            self.db_data = list(map(int, lines[1].strip().split()))  # 获取分布式数据库的位置

    def read_topo(self):
        # 读取所有时间片的拓扑
        self.num_slot = len(os.listdir(self.filePath + "/config/timeslot")) - 1    # 获取时间片个数
        for slot_no in range(self.num_slot):
            self.load_topo_a_slot(slot_no, self.filePath + "/config/timeslot/test_" + str(slot_no))   # 读取一个时间片的拓扑

    def load_topo_a_slot(self, slot_no, filename:str):
        # 从文件当中加载一个时间片
        with open(file=filename) as file:
            lines = file.read().splitlines()
            
            self.num_sw = int(lines[0].strip()) # 获取卫星交换机的数量
            del lines[0:2] # 删除前面的两行内容

            self.data_topos[slot_no] = dict()   # 通过邻接链表存储
            for sw in range(self.num_sw):
                self.data_topos[slot_no][sw] = dict()
            for line in lines:
                link = line.strip().split()
                sw1 = int(link[0])
                sw2 = int(link[1])
                self.data_topos[slot_no][sw1][sw2] = float(link[2])

    def diff_links(self):
        # 存储不同时间片之间需要改变的链路信息
        for slot_no in range(self.num_slot):
            self.diff_topo_a_slot(slot_no, (slot_no+1)%self.num_slot)   # 时间片切换对比

    def diff_topo_a_slot(self, slot_no1, slot_no2):
        # 找到时间片之间的不同链路信息，并存储下来。这里是slot_no1需要切换到slot_no2的时候，需要修改的链路，其中-1指删除，0指修改时延，1指添加链路，（type, sw1, sw2, delay）
        dslot_b = self.data_topos[slot_no1]
        dslot_n = self.data_topos[slot_no2]
        self.diff_topos[slot_no2] = dict()
        for sw in dslot_b:
            self.diff_topos[slot_no2][sw] = list()
            for adj_sw in dslot_b[sw]:
                if adj_sw not in dslot_n[sw]:
                    self.diff_topos[slot_no2][sw].append((-1, sw, adj_sw, dslot_b[sw][adj_sw]))
                elif dslot_b[sw][adj_sw] != dslot_n[sw][adj_sw]:
                    self.diff_topos[slot_no2][sw].append((0, sw, adj_sw, dslot_n[sw][adj_sw]))
        for sw in dslot_n:
            for adj_sw in dslot_n[sw]:
                if adj_sw not in dslot_b[sw]:
                    self.diff_topos[slot_no2][sw].append((1, sw, adj_sw, dslot_n[sw][adj_sw]))
