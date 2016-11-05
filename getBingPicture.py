#!/usr/bin/env python3
# coding=utf-8
#__author__='__tree__'
from bs4 import BeautifulSoup
from urllib.request import urlopen
from selenium import webdriver
import os
import socket
import threading
import re
import urllib
import time


def main():
    time_now = time.strftime('%Y-%m-%d', time.localtime()) # 获取当前系统时间
    time_last = '1234' #上一次保存图片时间
    while True:
        # 首先判断当天的图片有没有保存过
        if time_last == time_now:
            time.sleep(3600)
            time_now = time.strftime('%Y-%m-%d', time.localtime())
        else:
            # 开始获取图片
            print('开始获取图片：')
            driver = webdriver.PhantomJS(executable_path='phantomjs-2.1.1-windows/bin/phantomjs')#浏览器的地址
            driver.delete_all_cookies()
            driver.get("http://cn.bing.com")#目标网页地址
            time.sleep(30)  # 暂停30s
            html_bing = driver.page_source
            reg = r'background-image: url\((.*?)\);' #正则表达式
            pic_url = re.findall(reg,html_bing,re.S) # 寻找图片链接
            driver.close()
            i = 0
            for pic in pic_url:
                pic_data = urlopen(pic).read()  # 打开图片链接
                # 获取图片格式
                list_len = len(pic.split('.'))
                fileName = "bing/"+time_now+'_'+str(i)+'.'+pic.split('.')[list_len-1]
                fp = open(fileName,'wb')
                print("正在保存："+fileName)
                fp.write(pic_data)
                fp.close()
            time_last = time.strftime('%Y-%m-%d', time.localtime())

if __name__ == '__main__':
    main()