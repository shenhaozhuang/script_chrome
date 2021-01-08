#!/usr/bin/python3

import subprocess
import sys,os
import getopt
import argparse
import signal
import re
import socket
import time
import threading

import paramiko


GBK = 'gbk'
UTF8 = 'utf-8'
current_encoding = GBK
position = ""

g_directory="/mnt/stateful_partition/results/"+time.strftime("%Y%m%d_%H%M%S")
g_ip_current = [(s.connect(('8.8.8.8', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]
g_ip_guest=""
g_ip_host=""
g_test_cases=[]
g_case_pattern='TEMPLATE'

g_results_list = dict()
g_file_results = "%s/result.csv"%g_directory
g_fd_results = None

g_bool_max_cpu=False
g_bool_max_gpu=False


def signal_handler(sig, frame):
	print('Interruptted by user! (Ctrl+C)')
	# subprocess.run(['ssh %s pkill turbostat' %g_ip_host], shell=True)
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)


class Case:
	bin_case=""
	case_name=""
	file_testlog=""
	file_turbostatlog=""
	fd_testlog=None
	fd_turbostatlog=None
	base_directory=g_directory
	ip_host=g_ip_host

	file_topcpulog=""
	file_topgpulog=""
	fd_topcpulog=None
	fd_topgpulog=None

	result=""
	is_guest=False

	output_std=""
	run_list=[]
	case_pattern=''
	is_skipped=False
	conn_server_topcpu=None
	conn_server_topgpu=None
	conn_server_turbostat=None
	conn_server_prepare=None

	proc_server_topcpu=None
	proc_server_topgpu=None
	proc_server_turbostat=None
	proc_server_prepare=None

	def __init__(self, case_name, bin_case, is_guest):
		self.run_list=g_test_cases
		self.case_pattern=g_case_pattern
		self.case_name = case_name
		self.bin_case = bin_case
		self.file_testlog = "%s/%s.log"%(self.base_directory, case_name)
		self.file_turbostatlog = "%s/%s.turbostat"%(self.base_directory, case_name)
		self.file_topcpulog = "%s/%s.cpu"%(self.base_directory, case_name)
		self.file_topgpulog = "%s/%s.gpu"%(self.base_directory, case_name)

		self.is_guest = is_guest

		self.fd_testlog = open(self.file_testlog, "w+")
		self.fd_topcpulog = open(self.file_topcpulog, "w")
		self.fd_topgpulog = open(self.file_topgpulog, "w")
		self.fd_turbostatlog= open(self.file_turbostatlog, "w")

		found_case = re.search(self.case_pattern, self.case_name)
		if(((self.case_name not in self.run_list) and self.run_list != []) or (not found_case and self.case_pattern != '')):
			self.is_skipped=True

		if self.is_guest == "guest":
			self.conn_server_prepare = paramiko.SSHClient()
			self.conn_server_prepare.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_prepare.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_cpu = paramiko.SSHClient()
			self.conn_server_cpu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_cpu.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_gpu = paramiko.SSHClient()
			self.conn_server_gpu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_gpu.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_turbostat = paramiko.SSHClient()
			self.conn_server_turbostat.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_turbostat.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)
		elif self.is_guest == "chroot":
			self.conn_server_prepare = paramiko.SSHClient()
			self.conn_server_prepare.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_prepare.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_cpu = paramiko.SSHClient()
			self.conn_server_cpu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_cpu.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_gpu = paramiko.SSHClient()
			self.conn_server_gpu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_gpu.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_turbostat = paramiko.SSHClient()
			self.conn_server_turbostat.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_turbostat.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)
		elif self.is_guest == "android":
			self.conn_server_prepare = paramiko.SSHClient()
			self.conn_server_prepare.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_prepare.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_cpu = paramiko.SSHClient()
			self.conn_server_cpu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_cpu.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_gpu = paramiko.SSHClient()
			self.conn_server_gpu.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_gpu.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

			self.conn_server_turbostat = paramiko.SSHClient()
			self.conn_server_turbostat.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server_turbostat.connect(g_ip_host, 22, username='root', password='test0000', timeout=3)

		self.do_run()

	def result_parser(self, pattern, line_num=0):
		if(self.is_skipped):
			return
		self.fd_testlog.seek(0)
		stdout = self.fd_testlog.read()
		stdout_list = stdout.splitlines()
		ret_list = []
		try:
			if isinstance(line_num, list):
				for i in line_num:
					ret = re.search(pattern, stdout_list[i].strip()).group()
					ret_list.append(ret)
				print(ret_list)
				return ret_list
			elif line_num != 0:
				ret = re.search(pattern, stdout_list[line_num].strip()).group()
				print("result: %s" %ret)
				return ret
			else:
				# Not based on the number of rows
				ret = re.search(pattern, stdout).group(1)
				print("result: %s" %ret)
				return ret
		except:
			ret = None
			print("[Warn]:%s No output, or result pattern missing match!!"%self.case_name)
			return ret

	def do_run(self):
		if(self.is_skipped):
			print("[skipped]:", self.case_name)
			return
		if self.is_guest == "guest":
			self.do_run_guest()
		elif self.is_guest == "chroot":
			self.do_run_chroot()
		elif self.is_guest == "android":
			self.do_run_android()
		else:
			self.do_run_host()

	def do_run_host(self):
		p_turbostat = subprocess.Popen(['turbostat -s PkgWatt,CorWatt,GFXWatt,RAMWatt -q -i 1 --Summary'],
			shell=True, stdout=self.fd_turbostatlog, stderr=self.fd_turbostatlog)
		p_topcpu = subprocess.Popen(['./top_cpu.sh'], shell=True, stdout=self.fd_topcpulog, stderr=self.fd_topcpulog)
		p_topgpu = subprocess.Popen(['./top_gpu.sh'], shell=True, stdout=self.fd_topgpulog, stderr=self.fd_topgpulog)
		p_dropcache = subprocess.Popen(['echo 3 > /proc/sys/vm/drop_caches'], shell=True)

		print("[Running]: %s"%self.bin_case)
		p_test = subprocess.Popen([self.bin_case],
			shell=True,
			stdout = self.fd_testlog,
			stderr = self.fd_testlog,
			bufsize=0)
		p_test.wait()

		p_topgpu.kill()
		p_topcpu.kill()
		p_turbostat.kill()
		print("[Done]")

	def host_top_cpu(self):
		stdin, stdout, stderr = self.conn_server_cpu.exec_command("bash /mnt/stateful_partition/script_chrome/top_cpu.sh")
		self.fd_topcpulog.write(stdout.read().decode('utf-8'))
		self.fd_topcpulog.flush()
		self.fd_topcpulog.close()

	def host_top_gpu(self):
		stdin, stdout, stderr = self.conn_server_gpu.exec_command("bash /mnt/stateful_partition/script_chrome/top_gpu.sh")
		self.fd_topgpulog.write(stdout.read().decode('utf-8'))
		self.fd_topgpulog.flush()
		self.fd_topgpulog.close()

	def host_turbostat(self):
		stdin, stdout, stderr = self.conn_server_turbostat.exec_command("turbostat -s PkgWatt,CorWatt,GFXWatt,RAMWatt -q -i 1 --Summary")
		list = stdout.readlines()
		output = [line.rstrip() for line in list]
		self.fd_turbostatlog.write('\n'.join(output))

	def host_prepare(self):
		stdin, stdout, stderr = self.conn_server_prepare.exec_command("echo 3 > /proc/sys/vm/drop_caches")
		list = stdout.readlines()
		output = [line.rstrip() for line in list]

	def do_run_guest(self):
		self.proc_server_prepare=threading.Thread(target=self.host_prepare, args=())
		self.proc_server_prepare.start()
		self.proc_server_prepare.join()

		self.proc_server_topcpu=threading.Thread(target=self.host_top_cpu, args=())
		self.proc_server_topcpu.start()

		self.proc_server_topgpu=threading.Thread(target=self.host_top_gpu, args=())
		self.proc_server_topgpu.start()

		self.proc_server_turbostat=threading.Thread(target=self.host_turbostat, args=())
		self.proc_server_turbostat.start()

		print("[Running]: %s"%self.bin_case)
		p_test = subprocess.Popen([self.bin_case],
			shell=True,
			stdout = self.fd_testlog,
			stderr = self.fd_testlog,
			bufsize=0)
		p_test.wait()
		self.conn_server_prepare.close()
		self.conn_server_cpu.close()
		self.conn_server_gpu.close()
		self.conn_server_turbostat.close()
		self.proc_server_topcpu.join()
		self.proc_server_topgpu.join()
		self.proc_server_turbostat.join()
		time.sleep(1)
		print("[Done]")

	def do_run_android(self):
		self.proc_server_prepare=threading.Thread(target=self.host_prepare, args=())
		self.proc_server_prepare.start()
		self.proc_server_prepare.join()

		self.proc_server_topcpu=threading.Thread(target=self.host_top_cpu, args=())
		self.proc_server_topcpu.start()

		self.proc_server_topgpu=threading.Thread(target=self.host_top_gpu, args=())
		self.proc_server_topgpu.start()

		self.proc_server_turbostat=threading.Thread(target=self.host_turbostat, args=())
		self.proc_server_turbostat.start()
		print("[Running]: %s"%self.bin_case)
		p_test = subprocess.Popen([self.bin_case],
			shell=True,
			stdout = self.fd_testlog,
			stderr = self.fd_testlog,
			bufsize=0)
		p_test.wait()
		self.conn_server_prepare.close()
		self.conn_server_cpu.close()
		self.conn_server_gpu.close()
		self.conn_server_turbostat.close()
		self.proc_server_topcpu.join()
		self.proc_server_topgpu.join()
		self.proc_server_turbostat.join()
		time.sleep(1)
		print("[Done]")

	def do_run_chroot(self):
		self.proc_server_prepare=threading.Thread(target=self.host_prepare, args=())
		self.proc_server_prepare.start()
		self.proc_server_prepare.join()

		self.proc_server_topcpu=threading.Thread(target=self.host_top_cpu, args=())
		self.proc_server_topcpu.start()

		self.proc_server_topgpu=threading.Thread(target=self.host_top_gpu, args=())
		self.proc_server_topgpu.start()

		self.proc_server_turbostat=threading.Thread(target=self.host_turbostat, args=())
		self.proc_server_turbostat.start()
		print("[Running]: %s"%self.bin_case)
		p_test = subprocess.Popen([self.bin_case],
			shell=True,
			stdout = self.fd_testlog,
			stderr = self.fd_testlog,
			bufsize=0)
		p_test.wait()
		self.conn_server_prepare.close()
		self.conn_server_cpu.close()
		self.conn_server_gpu.close()
		self.conn_server_turbostat.close()
		self.proc_server_topcpu.join()
		self.proc_server_topgpu.join()
		self.proc_server_turbostat.join()
		time.sleep(1)
		print("[Done]")

def run_cases_host():
	print("Running test cases as a host")
	run_cases("host")
	# For host specified test case, create here
	case = Case("stream_Triad", "/mnt/stateful_partition/stream/stream", "host")
	# g_results_list[case.case_name + "_Copy"] = case.result_parser(r"[0-9]*\.[0-9]+", 19)
	# g_results_list[case.case_name + "_Scale"] = case.result_parser(r"[0-9]*\.[0-9]+", 20)
	# g_results_list[case.case_name + "_Add"] = case.result_parser(r"[0-9]*\.[0-9]+", 21)
	g_results_list[case.case_name] = case.result_parser(r"[0-9]*\.[0-9]+", 22)

	case = Case("geekbench_Single-Core-Score", "su chronos --command='/mnt/stateful_partition/data/local/tmp/geekbench_x86_64 --cpu --no-upload --single-core'", "host")
	g_results_list[case.case_name] = case.result_parser(r"Single-Core Score\s*([0-9]+)", 0)
	case = Case("geekbench_Multi-Core-Score", "su chronos --command='/mnt/stateful_partition/data/local/tmp/geekbench_x86_64 --cpu --no-upload --multi-core'", "host")
	g_results_list[case.case_name] = case.result_parser(r"Multi-Core Score\s*([0-9]+)", 0)
	# g_results_list[case.case_name + "_Single-Core-Score"] = case.result_parser(r"\d.*", 69)
	# g_results_list[case.case_name + "_Multi-Core-Score"] = case.result_parser(r"\d.*", 73)

	case = Case("iperf3", "iperf3 -c 192.168.3.7 -t 60 -i 60", "host")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{3,}', 7)

	case = Case("netperf-tcp_stream", "netperf -H 192.168.3.7 -t tcp_stream -l 60", "host")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{3,}\.[0-9]+', 6)

	case = Case("netperf-rr", "netperf -H 192.168.3.7 -t tcp_rr -l 60", "host")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{3,}\.[0-9]+', 6)

	case = Case("kernelCompilation", "cd /home/ikvmgt/linux/ && make clean && time make --directory=/mnt/statefule_partation/linux/ -j4", "host")
	time_list = case.result_parser(r'[0-9]+:[0-9]+\.[0-9]+', -2).split(":")
	g_results_list[case.case_name] = int(time_list[0])*60 + float(time_list[1])
	# g_results_list[case.case_name + "_user"] = case.result_parser(r'^[0-9]+\.[0-9]+', -2)
	# g_results_list[case.case_name + "_system"] = case.result_parser(r' [0-9]+\.[0-9]+', -2)

def run_cases_guest():
	print("Running test cases as a guest")
	run_cases("guest")
	# For guest specified test case, create here
	case = Case("kernelCompilation", "cd /home/ikvmgt/linux/ && make clean && time make --directory=/home/ikvmgt/linux/ -j4", "guest")
	time_list = case.result_parser(r'[0-9]+:[0-9]+\.[0-9]+', -2).split(":")
	g_results_list[case.case_name] = int(time_list[0])*60 + float(time_list[1])
	# g_results_list[case.case_name + "_user"] = case.result_parser(r'^[0-9]+\.[0-9]+', -2)
	# g_results_list[case.case_name + "_system"] = case.result_parser(r' [0-9]+\.[0-9]+', -2).strip()

	gfxbench4_list=[
	'car-chase.trace',
	'manhattan.trace', 
	't-rex.trace',
	]
	for game in gfxbench4_list:
		case = Case(game, "su ikvmgt -c 'glretrace /home/ikvmgt/gfxbench4/%s'"%game, "guest")
		g_results_list[case.case_name] = case.result_parser(r'([0-9]+\.[0-9]+) fps', 0)

	case = Case("nexuiz", "su ikvmgt -c 'nexuiz -benchmark demos/demo1 -nosound'", "guest")
	g_results_list[case.case_name] = case.result_parser(r"[0-9]{2}[.][0-9]{7}", -1)

	case = Case("openarena", "su ikvmgt -c 'openarena +exec anholt'", "guest")
	g_results_list[case.case_name] = case.result_parser(r"[0-9]{2,}\.+[0-9]+", -11)

	case = Case("glmark2", "su ikvmgt -c 'glmark2'", "guest")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{2,}\.?[0-9]?', 42)

	case = Case("geekbench_Single-Core-Score", "/data/local/tmp/geekbench_x86_64 --cpu --no-upload --single-core", "guest")
	g_results_list[case.case_name] = case.result_parser(r"Single-Core Score\s*([0-9]+)", 0)
	case = Case("geekbench_Multi-Core-Score", "/data/local/tmp/geekbench_x86_64 --cpu --no-upload --multi-core", "guest")
	g_results_list[case.case_name] = case.result_parser(r"Multi-Core Score\s*([0-9]+)", 0)
	# g_results_list[case.case_name + "_Single-Core-Score"] = case.result_parser(r"\d.*", 69)
	# g_results_list[case.case_name + "_Multi-Core-Score"] = case.result_parser(r"\d.*", 73)

	case = Case("stream_Triad", "/home/ikvmgt/stream/stream", "guest")
	# g_results_list[case.case_name + "_Copy"] = case.result_parser(r"[0-9]*\.[0-9]+", 19)
	# g_results_list[case.case_name + "_Scale"] = case.result_parser(r"[0-9]*\.[0-9]+", 20)
	# g_results_list[case.case_name + "_Add"] = case.result_parser(r"[0-9]*\.[0-9]+", 21)
	g_results_list[case.case_name] = case.result_parser(r"[0-9]*\.[0-9]+", 22)

	case = Case("iperf3", "iperf3 -c 192.168.3.7 -t 60 -i 60", "guest")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{3,}', 7)

	case = Case("netperf-tcp_stream", "netperf -H 192.168.3.7 -t tcp_stream -l 60", "guest")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{3,}\.[0-9]+', 6)

	case = Case("netperf-rr", "netperf -H 192.168.3.7 -t tcp_rr -l 60", "guest")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{3,}\.[0-9]+', 6)

def run_cases_android(): 
	print("Running test cases as a androidVM")
	# For androidVm specified test case, create here
	case = Case("geekbench_Single-Core-Score", "adb shell /data/local/tmp/geekbench_x86_64 --no-upload --cpu --single-core", "android")
	g_results_list[case.case_name] = case.result_parser(r"Single-Core Score\s*([0-9]+)", 0)
	case = Case("geekbench_Multi-Core-Score", "adb shell /data/local/tmp/geekbench_x86_64 --no-upload --cpu --multi-core", "android")
	g_results_list[case.case_name] = case.result_parser(r"Multi-Core Score\s*([0-9]+)", 0)
	# g_results_list[case.case_name + "_Single-Core-Score"] = case.result_parser(r"\d.*", 69)
	# g_results_list[case.case_name + "_Multi-Core-Score"] = case.result_parser(r"\d.*", 73)

def run_cases_chroot():
	print("Running test cases as a chroot")
	# For chroot specified test case, create here
	case = Case("nexuiz", "su intel -c 'nexuiz -benchmark demos/demo1 -nosound'", "guest")
	g_results_list[case.case_name] = case.result_parser(r"([0-9]+\.[0-9]+) fps", 0)

	case = Case("openarena", "su intel -c 'openarena +exec anholt'", "guest")
	g_results_list[case.case_name] = case.result_parser(r"([0-9]+\.[0-9]+) fps", 0)

	gfxbench4_list=[
	# 'car-chase.trace',
	# 'manhattan.trace', 
	't-rex.trace',
	]
	for game in gfxbench4_list:
		case = Case(game, "su intel -c 'glretrace /home/intel/gfxbench4/%s'"%game, "guest")
		g_results_list[case.case_name] = case.result_parser(r'([0-9]+\.[0-9]+) fps', 0)

	case = Case("glmark2", "su intel -c 'glmark2'", "guest")
	g_results_list[case.case_name] = case.result_parser(r'[0-9]{2,}\.?[0-9]?', 42)

def run_cases(is_guest):
	######## Add test cases here! For common test cases #############
	case = Case("fio-read", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=read -ioengine=libaio -size=512M -numjobs=4 -name=fio_read"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'READ: \S* \((\S*)MB/s\)', 0)

	case = Case("fio-write", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=write -ioengine=libaio -size=512M -numjobs=4 -name=fio_write"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'WRITE: \S* \((\S*)MB/s\)', 0)

	case = Case("fio-randread", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=randread -ioengine=libaio -size=512M -numjobs=4 -name=fio_randread"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'READ: \S* \((\S*)MB/s\)', 0)

	case = Case("fio-randwrite", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=randwrite -ioengine=libaio -size=512M -numjobs=4 -name=fio_randwrite"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'WRITE: \S* \((\S*)MB/s\)', 0)

def detele_file():
    print("[detele test_file]")
    deteleFile = subprocess.Popen("rm -rf %s/test_file"%g_directory, shell=True,bufsize=0)
    if deteleFile.returncode == 0:
        print("detele successful!")
    else:
        print("detele failed!")
    deteleFile.wait()

def main():
	global dir_output, g_bool_max_cpu, g_bool_max_gpu, g_ip_host, g_ip_guest, g_ip_chroot, g_case_pattern, g_test_cases

	# Add global arguments!
	parser = argparse.ArgumentParser(description='This is a simple automated test framework for ChromeOS and Linux VM')
	parser.add_argument('-d','--directory',
		help='The directory for saving results and logs. Default is /mnt/statefule_partation/<current_dateime>')
	parser.add_argument('-c', '--max-cpu', action="store_true", default=False, dest='bool_max_cpu',
		help='Online all CPU cores, only 2 out of 4 cores are enabled by default on Pixelbook; And force cpus running at highest freq!')
	parser.add_argument('-g', '--max-gpu', action="store_true", default=False, dest='bool_max_gpu',
		help='Force GPU running with highest freqency!')
	parser.add_argument('-H', '--host-ip', action="store", default="100.115.92.25", dest='ip_host',
		help='Specify IP of host side, default is 100.115.92.25 which is default value of pixelbook')
	parser.add_argument('-G', '--guest-ip', action="store", default="100.115.92.194", dest='ip_guest',
		help='Specify IP of guest side, which is random, have to be given')
	parser.add_argument('-C', '--chroot-ip', action="store", default="100.115.92.194", dest='ip_chroot',
		help='Specify IP of chroot side, which is random, have to be given')
	parser.add_argument('-t', '--test-case', action="append", type=str, nargs='?', default=[], dest='test_cases',
		help='Specify test cases list')
	parser.add_argument('-p', '--case-pattern', action="store", type=str, default='', dest='case_pattern',
		help='Specify test cases pattern string')

	# Add sub-command and its arguments!
	subparsers = parser.add_subparsers()

	parser_host = subparsers.add_parser('host', help="Run this test framework on a host machine")
	parser_host.set_defaults(func=run_cases_host)

	parser_guest = subparsers.add_parser('guest', help="Run this test framework on a linuxVM")
	parser_guest.set_defaults(func=run_cases_guest)

	parser_chroot = subparsers.add_parser('chroot', help="Run this test framework on a chroot")
	parser_chroot.set_defaults(func=run_cases_chroot)

	parser_android = subparsers.add_parser('android', help="Run this test framework on a androidVM")
	parser_android.set_defaults(func=run_cases_android)

	args = parser.parse_args()

	dir_output = getattr(args, 'directory', g_directory)
	if dir_output == None:
		dir_output = g_directory
	g_bool_max_cpu = args.bool_max_cpu
	g_bool_max_gpu = args.bool_max_gpu
	g_ip_host = args.ip_host
	g_ip_guest = args.ip_guest
	g_ip_chroot = args.ip_chroot
	g_test_cases = args.test_cases
	g_case_pattern= args.case_pattern

	# Sanity Check
	if not os.path.exists(dir_output):
		os.makedirs(dir_output)

	if g_bool_max_cpu:
		subprocess.call(["./max_cpu.sh"] )

	if g_bool_max_gpu:
		subprocess.call(["./max_gpu.sh"])

	# Run test cases, distinguish host and guest which given by command arguments
	args.func()

	#print(g_results_list)
	g_fd_results = open(g_file_results, 'w')
	g_fd_results.write('caseName, caseResult\n')
	for key,value in g_results_list.items():
		print('%s %s'%(key,value))
		g_fd_results.write('%s, %s\n'%(key,value))
	g_fd_results.close()
	
	# detele file
	detele_file()
	

if __name__ == "__main__":
    main()
