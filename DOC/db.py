#!/usr/bin/env python3
#-*- coding:utf-8 -*-
'''
	author:xuehao
	time:2016.3.29
	
	数据库接口模板
'''

'''
	全局变量，engine数据库引擎对象
	
'''
engine=None




########FUNCTIONS:
'''
	初始化数据库连接信息
'''
def create_engine(user='root',password='xh1008',database='test', host='127.0.0.1', port=3306):
	pass

'''
	select(command):
		输入为一个sql语句
		查询结果以列表的形式返回，每个元素为一个dic
'''
def select(command):
	pass


'''
	insert update delete
'''
def update(sql,*args):





########CLASSES:
'''
	数据库引擎对象
'''
class _Engine(object):
	def __init__(self,connect):
		self._connect=connect
	def connect(self):
		return self._connect()



#持有数据库连接的上下文对象:
class _DbCtx(threading.local):
	def __init__(self):
		self.connection=None
		self.transactions=0

	def is_init(self):
		return not self.connection is None

	def init(self):
		self.connection=_LasyConnection()
		self.transactions=0

	def cleanup(self):
		self.connection.cleanup()
		self.connection=None
	
	def cursor(self):
		return self.connection.cursor()

_db_ctx=_DbCtx()

class _ConnectionCtx(object):
	def __enter__(self):
		global _db_ctx
		self.should_cleanup=False
		if not _db_ctx.is_init():
			_db_ctx.init()
			self.should_cleanup=True
		return self
	
	def __exit__(self,exctype,exvalue,traceback):
		global _db_ctx
		if self.should_cleanup:
			_db_ctx.cleanup()

	def connection():
		return _ConnectionCtx()


