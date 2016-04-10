#!/usr/bin/env python3
#-*- coding:utf-8 -*-

__author__='xuehao'
'''
把config_default.py作为开发环境的标准配置	

通常，一个Web App在运行时都需要读取配置文件，比如数据库的用户名、口令等，在不同的环境中运行时，Web App可以通过读取不同的配置文件来获得正确的配置。

默认的配置文件应该完全符合本地开发环境，这样，无需任何设置，就可以立刻启动服务器。

如果要部署到服务器时，通常需要修改数据库的host等信息，直接修改config_default.py不是一个好办法，更好的方法是编写一个config_override.py，用来覆盖某些默认设置：
'''

###to run the script you should change the value 
configs={
	'db':{
	'host':'127.0.0.1',
	'port':3306,
	'user':'username',
	'password':'password',
	'db':'tablename'
	},
	'session':{
	'secret':'DarkFrameXue'
	}
}
