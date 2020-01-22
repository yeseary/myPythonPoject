# -*- coding: utf-8 -*-
# @Time    : 2020/1/15 21:57
# @Author  : westerchen
# @File    : cal_program_usage.py
# @Resume  : 进行程序内存占用的计算

import locale
import os
import subprocess
import sys
import time
from multiprocessing import Pool
from threading import Thread

import psutil

try:
    from queue import Queue, Empty
except ImportError:
    from Queue import Queue, Empty  # python 2.x


def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()


def os_command(command):
    pipe = os.popen(command, 'r')
    text = pipe.read()
    sts = pipe.close()
    if sts is None: sts = 0
    if text[-1:] == '\n': text = text[:-1]
    return sts, text


ENCODING = locale.getdefaultlocale()[1]


class ProcessResourcer(object):
    def __init__(self, pid, type='VmSize'):
        self.pid = pid
        self.type = type
        self.child_pid_set = {}
        # self.cmd = "cat /proc/{pid}/stats | grep {type}".format(pid=self.pid, )
        self.usage_num = 0
        self.pool = Pool(6)
        self.heartbeart = 2
        self.sum_cost = 0
        self.max_cost = 0
        self.file = open("mm_" + str(pid) + '.log', 'w')
        print("output log to {0}".format(self.file.name))
        self.last_heat = time.time()

    def sync(self):
        if time.time() - self.last_heat < self.heartbeart:
            return
        self.last_heat = time.time()
        # 检查进程下所有的子进程
        # 求解子进程下所有的子进程占用之和
        self.child_pid_set = set()
        get_child_pid(self.pid, self.child_pid_set)
        self.sum_cost = 0
        # self.pool.map(func=ProcessResourcer.get_type_usage_by_pid, iterable=self.child_pid_list)

        for _pid in self.child_pid_set.copy():
            singe_cost = 0
            try:
                singe_cost = ProcessResourcer.get_type_usage_by_pid(_pid, self.type, to_num=True)
                # print("singe cost:%s, of pid:%s" %(singe_cost, _pid))
            except Exception as err:
                self.child_pid_set.remove(_pid)
                singe_cost = 0
                print(err)
            self.sum_cost += singe_cost
        if self.sum_cost > self.max_cost:
            self.max_cost = self.sum_cost

        self.file.write(
            "time:{time}, type:{type}, now_cost: {human_size}, max_cost: {max_cost}, child_pids:{child_pids} \n".format(
                time=time.strftime("%x %X", time.localtime()), max_cost=ProcessResourcer.sizeof_fmt(self.max_cost),
                type=self.type, human_size=ProcessResourcer.sizeof_fmt(self.sum_cost), child_pids=self.child_pid_set))
        self.file.flush()

    def __add__(self, other):
        return self.usage_num + other.usage_num

    def __del__(self):
        self.file.flush()
        self.file.close()

    @staticmethod
    def get_type_usage_by_pid(pid, type='VmSize', to_num=False):
        cmd = "cat /proc/{pid}/status | grep {type}".format(pid=pid, type=type)
        ret_code, result = os_command(cmd)
        if ret_code == 0:
            res = ""
            first_flag = True
            for i in result.split("\t")[1]:
                if i != " " or not first_flag:
                    res += i
                    first_flag = False
                elif not first_flag:
                    res += i

            if to_num:
                return ProcessResourcer.convert_format_size_to_int(res)
            else:
                return res
        else:
            raise ValueError("get {0} {1} error".format(pid, type))

    @staticmethod
    def convert_format_size_to_int(format_size):
        """
        2551000 KB --> 2551000*1024
        :param formate_size:
        :return:
        """
        _format_size = format_size.upper()
        _size_num, _size_unit = _format_size.split(" ")
        unit_coff = 1024
        for unit in ['K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if unit in _size_unit:
                return int(_size_num) * unit_coff
            unit_coff *= 1024
        return int(_size_num)

    @staticmethod
    def sizeof_fmt(num, suffix='B'):
        """
        convert bytes to human readable
        :param num:
        :param suffix:
        :return:
        """
        for unit in ['', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'Y', suffix)


def get_child_pid(pid, pid_set):
    try:
        parent = psutil.Process(pid)
        pid_set.add(pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        pid_set.add(process.pid)
        # get_child_pid(process.pid, pid_set)
    return


def communicate(p, commands=None):
    if commands is not None:
        commands = str.encode(commands)
    stdout, stderr = p.communicate(commands)
    if stdout is not None:
        stdout = stdout.decode(ENCODING)
    if stderr is not None:
        stderr = stderr.decode(ENCODING)
    return stdout, stderr


if __name__ == "__main__":
    command = " ".join(sys.argv[1:])
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=os.environ, shell=True)
    _processor = ProcessResourcer(proc.pid, 'VmRSS')
    q = Queue()
    t = Thread(target=enqueue_output, args=(proc.stdout, q))
    t.daemon = True  # thread dies with the program
    t.start()
    while True:
        if subprocess.Popen.poll(proc) == 0:
            break
        _processor.sync()
        try:
            line = q.get_nowait()  # or q.get(timeout=.1)
        except Empty:
            time.sleep(0.1)
            pass
        else:
            print line.strip()
