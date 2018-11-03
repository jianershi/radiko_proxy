#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#modified from https://gist.github.com/takuya/7236db2f8a52eb461968f6eacd203294

import requests
import os, sys, datetime, argparse, re
import subprocess
import base64
import shlex
import logging
import time
import sh
import glob
#from sh import ffmpeg
from sys import argv
from config import station,m3u8_local_destination, MANAGED_local_folder_for_music_files

DEBUG = False
ffmpegStarted=False
testran = False
starttime = time.time()

#if (len(argv) > 1):
#	station = argv[1]
#else:
#	station = 'FMT'
auth_token = ""
auth_key = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"
key_offset = 0

def auth1():
	url = "https://radiko.jp/v2/api/auth1"
	headers = {}
	auth_response = {}
	headers = {
		"User-Agent": "curl/7.56.1",
		"Accept": "*/*",
		"X-Radiko-App":"pc_html5" ,
		"X-Radiko-App-Version":"0.0.1" ,
		"X-Radiko-User":"dummy_user" ,
		"X-Radiko-Device":"pc" ,
	}
	res = requests.get(url,headers=headers)
	auth_response["body"] = res.content
	auth_response["headers"] = res.headers
	return auth_response

def get_partial_key(auth_response):
	authtoken = auth_response["headers"]["x-radiko-authtoken"]
	offset    = auth_response["headers"]["x-radiko-keyoffset"]
	length    = auth_response["headers"]["x-radiko-keylength"]
	offset = int(offset)
	length = int(length)
	partialkey= auth_key[offset:offset+length]
	partialkey = base64.b64encode(partialkey.encode())

	# logging.info(f"authtoken: {authtoken}")
	# logging.info(f"offset: {offset}")
	# logging.info(f"length: {length}")
	# logging.info(f"partialkey: {partialkey}")

	return [partialkey,authtoken]

def auth2( partialkey, auth_token ) :
	url = "https://radiko.jp/v2/api/auth2"
	headers =  {
		"X-Radiko-AuthToken": auth_token,
		"X-Radiko-Partialkey": partialkey,
		"X-Radiko-User": "dummy_user",
		"X-Radiko-Device": 'pc' }
	res  = requests.get(url, headers=headers)
	txt = res.content
	area = txt
	print(txt)
	return area

def gen_temp_chunk_m3u8_url( url, auth_token ):
	headers =  {
		"X-Radiko-AuthToken": auth_token,
	}
	res  = requests.get(url, headers=headers)
	body = res.content
	lines = re.findall( '^https?://.+m3u8$' , body, flags=(re.MULTILINE) )
	# embed()
	return lines[0]


def print_cmd(m3u8,token):
	print ("mpv --http-header-fields='X-Radiko-Authtoken:"+token+"' http://f-radiko.smartstream.ne.jp/"+station+"/_definst_/simul-stream.stream/playlist.m3u8")

def getm3u8():
	res = auth1()
	ret = get_partial_key(res)
	token = ret[1]
	partialkey = ret[0]
	auth2( partialkey, token )
	url = "http://f-radiko.smartstream.ne.jp/"+station+"/_definst_/simul-stream.stream/playlist.m3u8"
	m3u8 = gen_temp_chunk_m3u8_url( url ,token)
	return ([m3u8,token])

def ending_process(line,stdin):
	print('stderr: ')
	print(line)
	print (starttime, time.time()-starttime)
	if ( time.time()-starttime > 3600*12 ):
		stdin.put("q")
	return False

def ending_process_new(line,stdin):
	global ffmpegStarted
	global starttime
        sys.stdout.write("'stderr:[%s]: %s" % (datetime.datetime.now(),line))
	sys.stdout.flush()
	#set ffmpegStarted global flag to indicate FFMPEG started successfully
	if ("Press [q] to stop" in line):
		ffmpegStarted=True
		return False
	if ( ffmpegStarted == True and ("for writing" not in line) and ("for reading" not in line)):
		stdin.put("q")
	return False

def ending_process_test(line,stdin):
	print (line)
	if (testran == False):
		if ("Press [q] to stop" in line):
			time.sleep(20)
			stdin.put("q")
	return False
	
def printing_output(line,stdin):
	print ('stdout:')
	print (line)
	return False

def regenerate_ffmpeg(m3u8,token):
        p = sh.ffmpeg("-user_agent", "Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1", "-headers", "X-Radiko-Authtoken:"+token, "-i", m3u8, "-hls_flags", "delete_segments", "-hls_allow_cache", "0", "-c:a", "copy", m3u8_local_destination, "-loglevel", "info", _err=(ending_process_test if DEBUG else ending_process_new),  _out=printing_output, _bg=True)
	return p

def remove_old_file():
	files = glob.glob(MANAGED_local_folder_for_music_files+"/tokyofm*.ts")
	for file in files:
		p = sh.rm(file)

def startover():
	global starttime
	global ffmpegStarted
	remove_old_file()
        [m3u8, token]= getm3u8()
        print_cmd(m3u8,token)

	#ffmpeg  sequence
	starttime = time.time()
	ffmpegStarted=False
        p=regenerate_ffmpeg(m3u8,token)
	#test only
	#time.sleep(20)
	#p.terminate()
	#return p
	#end of test
	p.wait()

def main():
	while True:
		startover()	
		#test only
		if (not DEBUG):
			time.sleep(5)

main()
#p=startover()
#p.terminate()
#p=startover()
#p.wait()

