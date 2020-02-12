#!/usr/bin/python3

import subprocess
import sys,os
import getopt, sys

import argparse
 
import signal
import re

import socket

import time
import paramiko
import threading

GBK = 'gbk'
UTF8 = 'utf-8'
current_encoding = GBK

g_directory="/mnt/stateful_partition/results/"+time.strftime("%Y%m%d_%H%M%S")
g_ip_guest=""
g_ip_host=""
g_test_cases=[]

g_results_list = dict()

g_bool_max_cpu=False
g_bool_max_gpu=False

def signal_handler(sig, frame):
	print('Interruptted by user! (Ctrl+C)')

	subprocess.run(['ssh %s pkill turbostat' %g_ip_host], shell=True)
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
	is_skipped=False
	conn_server=None
	proc_server_topcpu=None
	proc_server_topgpu=None
	proc_server_turbostat=None

	def __init__(self, case_name, bin_case, is_guest):
		self.run_list=g_test_cases
		self.case_name = case_name
		self.bin_case = bin_case
		self.file_testlog = "%s/%s.log"%(self.base_directory, case_name)
		self.file_turbostatlog = "%s/%s_turbostat.log"%(self.base_directory, case_name)
		self.file_topcpulog = "%s/%s_topcpu.log"%(self.base_directory, case_name)
		self.file_topgpulog = "%s/%s_topgpu.log"%(self.base_directory, case_name)

		self.is_guest = is_guest

		self.fd_testlog = open(self.file_testlog, "w")
		self.fd_topcpulog = open(self.file_topcpulog, "w")
		self.fd_topgpulog = open(self.file_topgpulog, "w")
		self.fd_turbostatlog= open(self.file_turbostatlog, "w")

		if(self.case_name not in self.run_list):
			self.is_skipped=True

		if(self.is_guest):
			self.conn_server = paramiko.SSHClient()
			self.conn_server.set_missing_host_key_policy(paramiko.AutoAddPolicy())
			self.conn_server.connect(g_ip_host, 22, username='root', password='test0000', timeout=2)

		self.do_run()

	def result_parser(self, pattern, line_num=0):
		if(self.is_skipped):
			return
		if line_num != 0:
			stdout = self.output_std.splitlines()[line_num]
		else:
			stdout = self.output_std

		try:
			ret = re.search(pattern, stdout).group(1)
		except:
			ret = None
			print(self.output_std)
			print(pattern)
			print(stdout)

		return ret

	def do_run(self):
		if(self.is_skipped):
			print("[skipped]:", self.case_name)
			return

		if self.is_guest:
			self.do_run_guest()
		else:
			self.do_run_host()

	def do_run_host(self):
		p_turbostat = subprocess.Popen(['turbostat -s PkgWatt,CorWatt,GFXWatt,RAMWatt -q -i 1 -o %s'%self.file_turbostatlog], shell=True)
		p_topcpu = subprocess.Popen(['./top_cpu.sh'], shell=True, stdout=self.fd_topcpulog, stderr=self.fd_topcpulog)
		p_topgpu = subprocess.Popen(['./top_gpu.sh'], shell=True, stdout=self.fd_topgpulog, stderr=self.fd_topgpulog)
# Do not handle stdout/errout of turbostat
# Use its output augument instead.
#			stdout = subprocess.PIPE,
#			stderr = subprocess.PIPE,
#			bufsize=1)
		
		print("[Running]: %s"%self.bin_case)
		p_test = subprocess.Popen([self.bin_case],
			shell=True,
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE,
			bufsize=0)
		
		while p_test.poll() is None:
			std_out = p_test.stdout.read().decode(current_encoding)
			self.output_std = std_out

			self.fd_testlog.write(std_out)
#		    sys.stdout.write(std_out)
			self.fd_testlog.flush()

		
# Do not handle stdout/errout of turbostat
# Use its output augument instead.
#		    r = p_turbostat.stdout.readline().decode(current_encoding)
#		    self.fd_turbostatlog.write(r)
#		    self.fd_turbostatlog.flush()
#		    sys.stdout.write(r)

		if p_test.poll() != 0: 
			err = p_test.stderr.read().decode(current_encoding)
			sys.stdout.write(err)
			self.fd_testlog.write(err)
			self.fd_testlog.flush()
		
		self.fd_testlog.close()
		p_turbostat.kill()
		p_topcpu.kill()
		p_topgpu.kill()
		print("[Done]")
#		self.fd_turbostatlog.close()

	def host_top_cpu(self):
		stdin, stdout, stderr = self.conn_server.exec_command("top_cpu.sh")
		list = stdout.readlines()
		output = [line.rstrip() for line in list]
		self.fd_topcpulog.write('\n'.join(output))

	def host_top_gpu(self):
		stdin, stdout, stderr = self.conn_server.exec_command("top_gpu.sh")
		list = stdout.readlines()
		output = [line.rstrip() for line in list]
		self.fd_topgpulog.write('\n'.join(output))

	def host_turbostat(self):
		stdin, stdout, stderr = self.conn_server.exec_command("turbostat -s PkgWatt,CorWatt,GFXWatt,RAMWatt -q -i 1")
		list = stdout.readlines()
		output = [line.rstrip() for line in list]
		self.fd_turbostatlog.write('\n'.join(output))


	def do_run_guest(self):
		subprocess.call(['ssh %s mkdir -p %s'%(self.ip_host, self.base_directory)], shell=True)
		self.proc_server_topcpu=threading.Thread(target=self.host_top_cpu, args=())
		self.proc_server_topcpu.start()

		self.proc_server_topgpu=threading.Thread(target=self.host_top_gpu, args=())
		self.proc_server_topgpu.start()

		self.proc_server_turbostat=threading.Thread(target=self.host_turbostat, args=())
		self.proc_server_turbostat.start()

		#self.host_top_cpu()
#		p_turbostat = subprocess.Popen(['ssh %s turbostat -s PkgWatt,CorWatt,GFXWatt,RAMWatt -q -i 1 -o %s'%(self.ip_host, self.file_turbostatlog)],shell=True)
#		p_topcpu = subprocess.Popen(['ssh %s top_cpu.sh'%self.ip_host], shell=True, stdout=self.fd_topcpulog, stderr=self.fd_topcpulog)
#		p_topgpu = subprocess.Popen(['ssh %s top_gpu.sh'%self.ip_host], shell=True, stdout=self.fd_topgpulog, stderr=self.fd_topgpulog)
		print("[Running]: %s"%self.bin_case)
		p_test = subprocess.Popen([self.bin_case],
			shell=True,
			stdout = subprocess.PIPE,
			stderr = subprocess.PIPE,
			bufsize=0)

		while p_test.poll() is None:
		    std_out = p_test.stdout.read().decode(current_encoding)
		    self.output_std = std_out

		    self.fd_testlog.write(std_out)
		    self.fd_testlog.flush()

		if p_test.poll() != 0:
		    err = p_test.stderr.read().decode(current_encoding)
		    sys.stdout.write(err)
		    self.fd_testlog.write(err)
		    self.fd_testlog.flush()

		self.fd_testlog.close()
#		p_turbostat.kill()
#		p_topcpu.kill()
#		p_topgpu.kill()
		self.conn_server.close()
		self.proc_server_topcpu.join()
		self.proc_server_topgpu.join()
		self.proc_server_turbostat.join()

		subprocess.run(['ssh %s pkill turbostat'%self.ip_host], shell=True)
		subprocess.run(['ssh %s pkill top_cpu.sh'%self.ip_host], shell=True)
		subprocess.run(['ssh %s pkill top_gpu.sh'%self.ip_host], shell=True)

		print("[Done]")

def run_cases_host():
	global g_ip_guest
	print("here is host")
	run_cases(False)

# For host specified test case, create here
	case = Case("iperf3", "iperf3 -c %s -t 60 -i 60"%g_ip_guest, False)
	g_results_list[case.case_name] = case.result_parser(r'.* (\S*) Gbits/sec.*receiver', 7)

	case = Case("netperf-tcp_stream", "netperf -H %s -t tcp_stream -l 60"%g_ip_guest, False)
	g_results_list[case.case_name] = case.result_parser(r'\S* +\S* +\S* +\S* +(\S*)', 6)

	case = Case("netperf-rr", "netperf -H %s -t tcp_rr -l 60"%g_ip_guest, False)
	g_results_list[case.case_name] = case.result_parser(r'\S* +\S* +\S* +\S* +(\S*)', 6)

def run_cases_guest():
	global g_ip_guest
	print("here is guest")
	if g_ip_guest == "":
		g_ip_guest = [(s.connect(('100.115.92.25', 53)), s.getsockname()[0], s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]

	run_cases(True)

# For guest specified test case, create here
	case = Case("iperf3", "iperf3 -c %s -t 60 -i 60"%g_ip_host, True)
	g_results_list[case.case_name] = case.result_parser(r'.* (\S*) Gbits/sec.*receiver', 7)

	case = Case("netperf-tcp_stream", "netperf -H %s -t tcp_stream -l 60"%g_ip_host, True)
	g_results_list[case.case_name] = case.result_parser(r'\S* +\S* +\S* +\S* +(\S*)', 6)

	case = Case("netperf-rr", "netperf -H %s -t tcp_rr -l 20"%g_ip_host, True)
	g_results_list[case.case_name] = case.result_parser(r'\S* +\S* +\S* +\S* +(\S*)', 6)

def run_cases(is_guest):
	######## Add test cases here! For common test cases #############
	case = Case("fio-read", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=read -ioengine=libaio -size=2G -numjobs=4 -name=fio_read && rm -rf %s/test_file"%(g_directory,g_directory), is_guest)
	g_results_list[case.case_name] = case.result_parser(r'READ: \S* \((\S*)MB/s\)', 0)

	case = Case("fio-write", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=write -ioengine=libaio -size=2G -numjobs=4 -name=fio_write"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'WRITE: \S* \((\S*)MB/s\)', 0)

	case = Case("fio-randread", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=randread -ioengine=libaio -size=2G -numjobs=4 -name=fio_randread"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'READ: \S* \((\S*)MB/s\)', 0)

	case = Case("fio-randwrite", "fio -filename=%s/test_file -direct=1 -iodepth 256 -rw=randwrite -ioengine=libaio -size=2G -numjobs=4 -name=fio_randwrite"%g_directory, is_guest)
	g_results_list[case.case_name] = case.result_parser(r'WRITE: \S* \((\S*)MB/s\)', 0)

#	case = Case("apitrace-alu-2.trace", "apitrace replay /home/ikvmgt/gfxbench4/alu-2.trace", is_guest)

def main():
	global g_test_cases, g_directory, g_bool_max_cpu, g_bool_max_gpu, g_ip_host, g_ip_guest

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
	parser.add_argument('-t', '--test-case', action="append", type=str, nargs='?', default=[], dest='test_cases',
		help='Specify test cases list')


# Add sub-command and its arguments!
	subparsers = parser.add_subparsers()

	parser_host = subparsers.add_parser('host', help="Run this test framework on a host machine")
	parser_host.set_defaults(func=run_cases_host)
	parser_host = subparsers.add_parser('guest', help="Run this test framework on a VM")
	parser_host.set_defaults(func=run_cases_guest)

	args = parser.parse_args()
	dir_output = getattr(args, 'directory')
	if dir_output == "":
		g_directory = dir_output

	g_bool_max_cpu = args.bool_max_cpu
	g_bool_max_gpu = args.bool_max_gpu
	g_ip_host = args.ip_host
	g_ip_guest = args.ip_guest

	g_test_cases = args.test_cases

	print(args)
	#sys.exit(0)
# Sanity Check
	if not os.path.exists(g_directory):
		os.makedirs(g_directory)

	if g_bool_max_cpu:
		subprocess.call(["./max_cpu.sh"] )

	if g_bool_max_gpu:
		subprocess.call(["./max_gpu.sh"])

# Run test cases, distinguish host and guest which given by command arguments
	args.func()

	#print(g_results_list)
	for key,value in g_results_list.items():
		print('%s %s'%(key,value))


if __name__ == "__main__":
    main()
