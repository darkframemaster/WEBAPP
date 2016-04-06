#!/usr/bin/env python3
#-*- coding:utf-8 -*-

__author__='xuehao'


'''
	web app建立在asyncio上,
	这是用aiohttp写的一个基本的app.py
'''

import logging;logging.basicConfig(level=logging.INFO)
import asyncio,os,json,time

from datetime import datetime
from aiohttp import web
from jinja2 import Environment,FileSystemLoader
from config import configs

import orm
from webFrame import add_routes,add_static
from handlers import cookie2user,COOKIE_NAME


'''
	jinja2 用在这里是添加  html模板的
	该函数将app[__templating__]设置为jinja2中的Enviroment类型实例
	用到了一些option的设置
	还有filters，
'''
def init_jinja2(app,**kw):
	logging.info('init jinja2...')
	#初始化模板配置，包括模板运行代码的开始结束标识符，变量的开始结束标识符等
	options=dict(
		 # 是否转义设置为True，就是在渲染模板时自动把变量中的<>&等字符转换为&lt;&gt;&amp;
		autoescape=kw.get('autoescape',True),# 运行代码的开始标识符
		block_start_string=kw.get('block_start_string','{%'),# 运行代码的结束标识符
		block_end_string=kw.get('block_end_string','%}'), # 变量开始标识符
		variable_start_string=kw.get('variable_start_string','{{'),# 变量结束标识符
		variable_end_string=kw.get('variable_end_string','}}'),
		 # Jinja2会在使用Template时检查模板文件的状态，如果模板有修改， 则重新加载模板。如果对性能要求较高，可以将此值设为False		
		auto_reload=kw.get('auto_reload',True)
	)
	# 从参数中获取path字段，即html模板文件的位置
	path=kw.get('path',None)
	# 如果没有，则默认为当前文件目录下的 templates 目录
	if path is None:
		path=os.path.join(os.path.dirname(os.path.abspath(__file__)),'templates')
	logging.info('set jinja2 template path:%s'% path)
	#Enviroment 是jinja2中的一个核心类，它的实例用来保存配置，全局对象，以及从本地文件系统或者其他位置加载模板，这里把要加载的模板和配置传给Enviroment，生成Enviroment实例	
	env=Environment(loader=FileSystemLoader(path),**options)
	#从参数取filter字段
	#filters：一个字典描述的filters过滤器集合，如果没有模板被加载的时候，可以安全的添加filters或移除的.
	filters=kw.get('filters',None)
	if filter is not None:
		for name,f in filters.items():
			env.filters[name]=f
	#给webapp设置模板
	app['__templating__']=env

'''
	middleware拦截器设置
	middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。

	一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回。middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。
'''
@asyncio.coroutine
def logger_factory(app,handler):#handler=response
	@asyncio.coroutine
	def logger(request):
		logging.info('Request: %s,%s'% (request.method,request.path))
		return (yield from handler(request))
	return logger

@asyncio.coroutine
def data_factory(app,handler):
	@asyncio.coroutine
	def parse_date(request):
		if request.content_type.startswith('application/json'):
			request.__data__=yield from request.json()
			logging.info('request json: %s'%str(request.__data__))
		elif request.content_type.startswith('application/x-www-form-urlencoded'):
			request.__data__=yield from requset.post()
			logging.info('request form:%s'%str(request.__data__))
		return (yield from handler(request))
	return parse_data

@asyncio.coroutine
def auth_factory(app,handler):
	@asyncio.coroutine
	def auth(request):
		logging.info('check user:%s %s'% (request.method,request.path))
		request.__user__=None
		cookie_str=request.cookies.get(COOKIE_NAME)
		if cookie_str:
			user=yield from cookie2user(cookie_str)
			if user:
				logging.info('set current user:%s'% user.email)
				request.__user__=user
		if request.path.startswith('/manage/')and(request.__user__ is None or request.__user__.admin):
			return web.HTTPFound('/signin')
		return (yield from handler(request))
	return auth
	
@asyncio.coroutine
def response_factory(app,handler):
	@asyncio.coroutine
	def response(request):
		logging.info('Response handler...')
		r=yield from handler(request)
		logging.info('r = %s'% str(r))
		if isinstance(r,web.StreamResponse):
			return r
		if isinstance(r,bytes):
			resp=web.Response(body=r)
			resp.content_type='application/octet-stream'
			return resp
		if isinstance(r,str):
			if r.startswith('redirect:'):	
				return web.HTTPFound(r[9:])
			resp=web.Response(body=r.encode('utf-8'))
			resp.content_type='text/html;charset=utf-8'
			return resp
		if isinstance(r,dict):
			template =r.get('__template__')
			if template is None:
				resp=web.Response(body=json.dumps(r,ensure_ascii=False,default=lambda o: o.__dict__).encode('utf-8'))
				resp.content_type='application/json;charset=utf-8'
				return resp
			else:
				resp=web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
				resp.content_type='text/html;charset=utf-8'
				return resp
		if isinstance(r,int) and r>=100 and r<=600:
			return web.Response(r)
		if isinstance(r,tuple)and len(r)==2:
			t,m=r
			if isinstance(t,int)and t>=100 and t<600:
				return web.Response(status=t,text=str(m))
			resp=web.Response(body=str(r).encode('utf-8'))
			resp.content_type='text/plain;charset=utf-8'
			return resp
	return response

'''
	jinja中使用的filter
'''
def datetime_filter(t):
	delta=int(time.time() - t)
	if delta<60:
		return u'1分钟前'
	if delta<3600:
		return u'%s分钟前'% (delta // 60)
	if delta<86400:
		return u'%s小时前'% (delta // 3600)
	if delta<604800:
		return u'%s天前' % (delta // 86400)
	dt=datetime.fromtimestamp(t)
	return u'%s年%s月%s日' % (dt.year,dt.month,dt.day)
		

'''
	服务器
'''
@asyncio.coroutine
def init(loop):
	#connect to the database
	yield from orm.create_pool(loop=loop,**configs.db)
	'''
	Application源码middlewares的处理
	for factory in middlewares:
        	assert asyncio.iscoroutinefunction(factory), factory
        self._middlewares = list(middlewares)
	'''
	app=web.Application(loop=loop,middlewares=[logger_factory,auth_factory,response_factory])
	#jinja2 input html template loader
	init_jinja2(app,filters=dict(datetime=datetime_filter))
	#use the FUNC in webFrame to add the html files
	add_routes(app,'handlers')
	add_static(app)
	#create the net server
	srv=yield from loop.create_server(app.make_handler(),'127.0.0.1',9000)
	logging.info('server started at http://127.0.0.1:9000...')
	return srv


'''
# 响应处理
# 总结下来一个请求在服务端收到后的方法调用顺序是:
#     	logger_factory->response_factory->RequestHandler().__call__->get或post->handlers
# 那么结果处理的情况就是:
#     	由handler构造出要返回的具体对象
#     	然后在这个返回的对象上加上'__method__'和'__route__'属性，以标识别这个对象并使接下来的程序容易处理
#     	RequestHandler目的就是从URL函数中分析其需要接收的参数，从request中获取必要的参数，调用URL函数,然后把结果返回给response_factory
#     	response_factory在拿到经过处理后的对象，经过一系列对象类型和格式的判断，构造出正确web.Response对象，以正确的方式返回给客户端
# 在这个过程中，我们只用关心我们的handler的处理就好了，其他的都走统一的通道，如果需要差异化处理，就在通道中选择适合的地方添加处理代码。
# 在response_factory中应用了jinja2来套用模板
'''	


#run
loop=asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()

