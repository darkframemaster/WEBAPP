#!/usr/bin/env python3
#-*- coding:utf-8 -*-
import config_default

class Dict(dict):
	'''
	Simple dict but support access as x.y style.
	'''
	def __init__(self,names=(),values=(),**kw):
		super(Dict,self).__init__(**kw)
		for k,v in zip(names,values):
			self[k]=v

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Dict' object has no attribute '%s'"% key)
	
	def __setattr__(self,key,value):
		self[key]=value
	
#override配置覆盖default配置
#递归

def merge(default,override):
	r={}
	for k,v in default.items():
		if k in override:
			#如果有嵌套的配置，递归覆盖
			if isinstance(v,dict):
				r[k]=merge(v,override[k])
			else:
				r[k]=override[k]
		else:
			r[k]=v
	return r

#把配置文件转换为Dict类实例
def toDict(d):
	D=Dict()
	for k,v in d.items():
		D[k]=toDict(v) if isinstance(v,dict) else v
	return D
'''
main program
'''
#configs默认为默认配置
configs=config_default.configs
try:
	import config_override
	configs=merge(configs,config_override.configs)
except ImportError:
	pass
configs=toDict(configs)
