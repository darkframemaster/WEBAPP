#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import functools

'''
装饰器(Decorator)
'''

'''
本质上，decorator就是一个返回函数的高阶函数。
*args -- () 
**kw -- {}

def func(*arg,**kw):可以接受任何参数，包括没有参数

@functools.wraps(func)
使被装饰的函数名字不变
'''
def log(func):
	#@functools.wraps(func)
	def wrapper(*args,**kw):
		print('call %s():'% func.__name__)
		return func(*args,**kw)
	return wrapper

'''
函数也是可以赋值的
now=log(now)用Decorator表示如下
'''
@log
def now():
	print('2016-3-29')


#调用now
now()
print(now.__name__)

'''
decorator需要参数，需要编写一个返回decorator 的高阶函数
'''
def log_two(text):
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			print('%s %s():'%(text,func.__name__))
			return func(*args,**kw)
		return wrapper			
	return decorator

@log_two('execute')
def now_two():
	print('2016-3-29')

now_two()
print(now_two.__name__)
