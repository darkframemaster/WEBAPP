#!/usr/bin/env python3
#-*- coding:utf-8 -*-

author='xuehao'

'''
	Web框架的设计是完全从使用者出发，目的是让使用者编写尽可能少的代码。


'''
import asyncio 
import os
import inspect
import logging
import functools

from urllib import parse
from aiohttp import web
from apis import APIError


'''
@get and @post	函数装饰器

装饰get 和 post的函数获取URL信息
'''
def get(path):
	'''
		Define decorator @get('/path')	
	'''
	def decorator(func):
		@functools.wraps(func)	#让被装饰的函数名称不变
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__='GET'
		wrapper.__route__=path
		return wrapper
	return decorator

def post(path):
	'''
		Define decorator @path('/path')
	'''
	def decorator(func):
		@functools.wraps(func)
		def wrapper(*args,**kw):
			return func(*args,**kw)
		wrapper.__method__='POST'
		wrapper.__route__=path
		return wrapper
	return decorator


'''
 -- 使用inspect模块中的signature方法来获取函数的参数，实现一些复用功能--
 关于inspect.Parameter 的  kind 有5种：
 POSITIONAL_ONLY		只能是位置参数
 POSITIONAL_OR_KEYWORD		可以是位置参数也可以是关键字参数
 VAR_POSITIONAL			相当于是 *args
 KEYWORD_ONLY			关键字参数且提供了key，相当于是 *,key
 VAR_KEYWORD			相当于是 **kw

	signature(fn):	如果fn是函数返回fn的参数
	为了方便使用，返回元组
	DOC:https://docs.python.org/3/library/inspect.html#inspect.Parameter

	parameters:
    	An ordered mapping of parameters’ names to the corresponding Parameter objects.
	class inspect.Parameter(name, kind, *, default=Parameter.empty, annotation=Parameter.empty)

'''
def get_required_kw_args(fn):	
	#如果url处理函数需要传入关键字参数，且默认是空得话，获取这个key
	args=[]
	params=inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind==inspect.Parameter.KEYWORD_ONLY and param.default==inspect.Parameter.empty:
			args.append(name)
	return tuple(args)

def get_named_kw_args(fn):
	# 如果url处理函数需要传入关键字参数，获取这个key
	args=[]
	params=inspect.signature(fn).parameters
	for name,param in params.items():
		if param.kind ==inspect.Parameter.KEYWORD_ONLY:
           		args.append(name)
	return tuple(args)



def has_named_kw_args(fn):  
	# 判断是否有指定命名关键字参数
    	params = inspect.signature(fn).parameters
    	for name, param in params.items():
        	if param.kind == inspect.Parameter.KEYWORD_ONLY:
            		return True

def has_var_kw_arg(fn):  
	# 判断是否有关键字参数，VAR_KEYWORD对应**kw
    	params = inspect.signature(fn).parameters
    	for name, param in params.items():
        	if param.kind == inspect.Parameter.VAR_KEYWORD:
            		return True

# 判断是否存在一个参数叫做request，并且该参数要在其他普通的位置参数之后，即属于*kw或者**kw或者*或者*args之后的参数
def has_request_arg(fn):
	sig=inspect.signature(fn)
	params=sig.parameters
	found=False
	for name,param in params.items():
		if name=='request':
			found=True
			continue
		if found and (param.kind!=inspect.Parameter.VAR_POSITIONAL and param.kind!=inspect.Parameter.KEYWORD_ONLY and param.kind!=inspect.Parameter.VAR_KEYWORD):
			raise ValueError('request parameter must be the last named parameter in function:%s%s'%(fn.__name__,str(sig)))
	return found


'''
URL处理函数不一定是一个coroutine，因此我们用RequestHandler()来封装一个URL处理函数。
	
RequestHandler是一个类，由于定义了__call__()方法，因此可以将其实例视为函数。

RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数，然后把结果转换为web.Response对象，这样，就完全符合aiohttp框架的要求：

'''
class RequestHandler(object):
	def __init__(self,app,fn):
		self._app=app
		self._func=fn
		self._has_request_arg=has_request_arg(fn)
		self._has_var_kw_arg=has_var_kw_arg(fn)
		self._has_named_kw_args=has_named_kw_args(fn)

		self._named_kw_args=get_named_kw_args(fn)
		self._required_kw_args=get_required_kw_args(fn)
		print('------------_has_request_arg:%s'%self._has_request_arg)
		params=inspect.signature(fn).parameters
		for name,param in params.items():
			print('-------type-------:',param.kind)
	
	'''
		__call__
		* kw保存参数
		* 判断request是否存在参数，如果存在则根据是POST还是GET方法将参数内容保存到kw
		* 如果kw为空（说明request没有参数），将match_info列表里面的资源映射表赋值给kw，如果不为空把关键字参数的内容给kw
		
	'''
	
	#对request的处理
	@asyncio.coroutine
	def __call__(self,request):
		kw=None
		#如果fn有参数		
		if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
			#POST请求
			if request.method=='POST':
				if not request.content_type:
					return web.HTTPBadRequest('Missing Content-Type.')
				ct=request.content_type.lower()
				if ct.startswith('application/json'):
					#json请求
					params=yield from request.json()
					if not isinstance(params,dict):
						return web.HTTPBadRequest('JSON body must be object.')
					kw=params
				elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
					# 调用post方法，注意此处已经使用了装饰器
					params=yield from request.post()
					kw=dict(**params)
				else:
					return web.HTTPBadRequest('Unsupported Content-Type:%s'% request.content_type)
			#GET请求
			if request.method=='GET':
				qs=request.query_string
				if qs:
					kw=dict()
					# 该方法解析url中?	后面的键值对内容保存到kw
					for k,v in parse.parse_qs(qs,True).items():
						kw[k]=v[0]
		

		# 参数为空说明没有从Request对象中获取到必要参数
		if kw is None:
		# 此时kw指向match_info属性，一个变量标识符的名字的dict列表。Request中获取的命名关键字参数必须要在这个dict当中
			kw=dict(**request.match_info)
			print('kw:',kw)
		else:
		#如果从Request对象中获取到参数了
		#当没有可变参数，有命名关键字参数时候，kw命名关键字参数的内容		
			if not self._has_var_kw_arg and self._named_kw_args:
				copy=dict()
				for name in self._named_kw_args:
					if name in kw:	
						copy[name]=kw[name]
				kw=copy
			# check named arg: 检查命名关键字参数的名字是否和match_info中的重复
			for k,v in request.match_info.items():
				if k in kw:
					logging.warning('Duplicate arg name in named arg and kw args:%s'%k)
				kw[k]=v


		#如果有request这个参数，则把request对象加入kw['request']
		if self._has_request_arg:
			kw['request']=request
		#check required kw: 检查是否有必要关键字参数		
		if self._required_kw_args:
			for name in self._required_kw_args:
				if name not in kw:
					return web.HTTPBadRequest('Missing argument:%s'% name)
		logging.info('call with args: %s'% str(kw))
		try:
			r=yield from self._func(**kw)
			return r
		except APIError as e:
			return dict(error=e.error,data=e.data,message=e.message)


'''
----------------ADD router------------------

'''

#添加静态页面的路径
def add_static(app):
	path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'static')
	#app是aiohttp库里的对象，通过router.add_router方法可以指定处理函数
	app.router.add_static('/static/',path)
	logging.info('add static %s=>%s'% ('/static/',path))	


def add_route(app,fn):
	# add_route函数，用来注册一个URL处理函数
     	# 获取'__method__'和'__route__'属性，如果有空则抛出异常
	method=getattr(fn,'__method__',None)
	path=getattr(fn,'__route__',None)
	if path is None or method is None:
		raise ValueError('@get or @post not defined in %s'% str(fn))
	#如果fn不是协程(@asyncio.coroutine)修饰的并且fn还不是一个生成器，那么强行修饰为协程
	if not asyncio.iscoroutinefunction(fn)and not inspect.isgeneratorfunction(fn):
		fn=asyncio.coroutine(fn)
	logging.info('add route %s %s => %s (%s)'% (method,path,fn.__name__,', '.join(inspect.signature(fn).parameters.keys())))
	#正式注册为相应的url
	#处理fn获取url的方法为RequestHandler的自醒函数 '__call__'
	app.router.add_route(method,path,RequestHandler(app,fn))


def add_routes(app,module_name):
    	# 找到要引入的模块，找出传入的module_name的'.',因为一般都是name.py
    	# Python rfind() 返回字符串最后一次出现的位置，如果没有匹配项则返回-1
	n=module_name.rfind('.')
	logging.info('n=%s',n)
	# 没有'.',则传入的是module名
	'''__import__()在官方文档中不建议使用
	如果只是简单的用名字引入一模块，建议用importlib.import_module()
	'''
	if n==(-1):
		mod=__import__(module_name,globals(),locals())
		logging.info('globals=%s',globals()['__name__'])
	else:
		mod=__import__(module_name[:n],globals(),locals())
	for attr in dir(mod):
		#starts with('xxx'):是否以xxx开头
		#以_开头的一律跳过，我们定义的处理方法不是以_开头的，大多数以_开头的都是些自己封装的属性或者函数
		if attr.startswith('_'):
			continue
		fn =getattr(mod,attr)
		#只处理函数
		if callable(fn):
			method=getattr(fn,'__method__',None)
			path=getattr(fn,'__route__',None)
			if method and path:
				#如果fn里面有method和path，说明是我们定义的方法一般都有@get||@post，，加入达app的对象处理route中			
				add_route(app,fn) 
