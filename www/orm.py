#!/usr/bin/env python3
#-*- coding:utf-8 -*-


__author__='xuehao'

import asyncio,logging
import aiomysql
import pdb

def log(sql,args=()):
	logging.info('SQL:%s'% sql)

'''
	创建连接池
	每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
	连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务	

'''
@asyncio.coroutine
def create_pool(loop,**kw):
	logging.info('create database connection pool...')
	global __pool
	#connect to the db and return the value to _pool
	__pool=yield from aiomysql.create_pool(
		host=kw.get('host','localhost'),
		port=kw.get('port',3306),
		user=kw['user'],
		password=kw['password'],
		db=kw['db'],
		charset=kw.get('charset','utf8'),
		autocommit=kw.get('autocommit',True),
		maxsize=kw.get('maxsize',10),
		minsize=kw.get('minsize',1),
		loop=loop
	)

'''
	select
	SQL语句的占位符是?，而MySQL的占位符是%s，select()函数在内部自动替换。注意要始终坚持使用带参数的SQL，而不是自己拼接SQL字符串，这样可以防止SQL注入攻击。
	yield from将调用一个子协程（也就是在一个协程中调用另一个协程）并直接获得子协程的返回结果。

	如果传入size参数，就通过fetchmany()获取最多指定数量的记录，否则，通过fetchall()获取所有记录。
'''
@asyncio.coroutine
def select(sql,args,size=None):
	log(sql,args)
	global __pool
	with (yield from __pool) as conn:
		cur=yield from conn.cursor(aiomysql.DictCursor)
		yield from cur.execute(sql.replace('?','%s'),args or ())
		if size:
			rs=yield from cur.fetchmany(size)
		else:
			rs=yield from cur.fetchall()
		yield from cur.close()
		logging.info('rows returned:%s'% len(rs))
		return rs

'''
	insert ,update , delete
	要执行INSERT、UPDATE、DELETE语句，可以定义一个通用的execute()函数，因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数：
	execute()函数和select()函数所不同的是，cursor对象不返回结果集，而是通过rowcount返回结果数。
'''
@asyncio.coroutine
def execute(sql,args,autocommit=True):
	log(sql)
	with (yield from __pool) as conn:
		if not autocommit:
			yield from conn.begin()
		try:
			cur=yield from conn.cursor()
			yield from cur.execute(sql.replace('?','%s'),args)
			affected=cur.rowcount
			yield from cur.close()
			if not autocommit:
				yield from conn.commit()			
		except BaseException as e:
			if not autocommit:
				yield from conn.rollback()
			raise
		return affected




'''
	Field和各种Field子类
	数据库的类型定义

'''
class Field(object):

	def __init__(self,name,column_type,primary_key,default):
		self.name=name
		self.column_type=column_type
		self.primary_key=primary_key
		self.default=default
	
	def __str__(self):
		return '<%s,%s:%s>'%(self.__class__.__name__,self.column_type,self.name)

#string
class StringField(Field):
	def __init__(self,name=None,primary_key=False,default=None,ddl='varchar(100)'):
		super().__init__(name,ddl,primary_key,default)

#Boolean
class BooleanField(Field):
    	def __init__(self, name=None, default=False):
        	super().__init__(name, 'boolean', False, default)

#Integer
class IntegerField(Field):
    	def __init__(self, name=None, primary_key=False, default=0):
        	super().__init__(name, 'bigint', primary_key, default)

#Float
class FloatField(Field):
    	def __init__(self, name=None, primary_key=False, default=0.0):
        	super().__init__(name, 'real', primary_key, default)

#Text
class TextField(Field):
    	def __init__(self, name=None, default=None):
        	super().__init__(name, 'text', False, default)


'''
	ORM


	设计ORM需要从上层调用者角度来设计。
	我们先考虑如何定义一个User对象，然后把数据库表users和它关联起来。

	注意到定义在User类中的__table__、id和name是类的属性，不是实例的属性。所以，在类级别上定义的属性用来描述User对象和表的映射关系，而实例属性必须通过__init__()方法去初始化，所以两者互不干扰：


from orm import Model,StringField,IntegerField

class User(Model):
	__table__='users'
	
	id=IntegerField(primary_key=True)
	name=StringField()

'''

'''

	ModelMetaclass 元类 各种映射
    # 该元类主要使得Model基类具备以下功能:
    # 1.任何继承自Model的类（比如User），会自动通过ModelMetaclass扫描映射关系
    # 并存储到自身的类属性如__table__、__mappings__中
    # 2.创建了一些默认的SQL语句

	create_args_string 用于ModelMetaclass里面，将num以'?,?,?,?...,?'的方式返回
'''
def create_args_string(num):
	L=[]
	for n in range(num):
		L.append('?')
	return ', '.join(L)

class ModelMetaclass(type):
	'''	cls 	1.当前准备创建的类的对像
		name	2.类的名字
		bases	3.类继承的父类集合
		attrs	4.类的属性集合在代码中(attrs,type)==>(k,v)'''

	def __new__(cls,name,bases,attrs):
		#print('-------------------Metaclass-----------------')
		#print(cls.__name__,'----------->',name)
		#排除Model类
		if name=='Model':
			return type.__new__(cls,name,bases,attrs)
		#获取table名称
		tableName=attrs.get('__table__',None)or name
		logging.info('found model:%s (table:%s)'% (name,tableName))
		#获取所有的Field和主键名
		mappings=dict()	#映射
		fields=[]	#属性
		primaryKey=None	#主键
		#print('--------------------attrs------------------')
		for k,v in attrs.items():
			#print('found mapping:%s==>%s'% (k,v))
			#判断v是不是Field类型	
			if isinstance(v,Field):
				logging.info('found mapping:%s==>%s'% (k,v))
				mappings[k]=v
				if v.primary_key:
					#找到主键
					if primaryKey:
						raise RuntimeError('Duplicate primary key for field:%s'% k)
					primaryKey=k
				else:
					fields.append(k)
		#print('\n')
		if not primaryKey:
			raise RuntimeError('Primary key not found.')
		for k in mappings.keys():
			attrs.pop(k)
		#map(func,listorsth)
		#讲各种属性都转为字符串
		escaped_fields=list(map(lambda f:'`%s`'%f,fields))
		attrs['__mappings__']=mappings# 保存属性和列的映射关系
		attrs['__table__']=tableName
		attrs['__primary_key__']=primaryKey# 主键属性名
		attrs['__fields__']=fields# 除主键外的属性名
		
		# 构造默认的SELECT, INSERT, UPDATE和DELETE语句:
		#char.join(string)	用char将string分割
		#select attrs from `tablename`
		attrs['__select__']='select `%s`,%s from `%s`'%(primaryKey,','.join(escaped_fields),tableName)
		#insert into tablename (attrs)values(?,?...)
		attrs['__insert__']='insert into `%s` (%s,`%s`)values(%s)'%(tableName,','.join(escaped_fields),primaryKey,create_args_string(len(escaped_fields)+1))
		#update `tablename` set attrs=? where primaryKey=? 
		attrs['__update__']='update `%s` set %s where `%s`=?'%(tableName,','.join(map(lambda f:'`%s`=?'%(mappings.get(f).name or f),fields)),primaryKey)
		#delete from `tablename` where `primaryKey`=?
		attrs['__delete__']='delete from `%s` where `%s`=?'%(tableName,primaryKey)
		return type.__new__(cls,name,bases,attrs)	




'''
	Model:ORM映射基类

'''
'''
		封装数据库的调用方法，用参数拼sql语句并执行
'''
class Model(dict,metaclass=ModelMetaclass):
	def __init__(self,**kw):
		super(Model,self).__init__(**kw)

	def __getattr__(self,key):
		try:
			return self[key]
		except KeyError:
			raise AttributeError(r"'Model' object has no attribute '%s'"% key)
	
	def __setattr__(self,key,value):
		self[key]=value
	
	def getValue(self,key):
		return getattr(self,key,None)
		
	def getValueOrDefault(self,key):
		value=getattr(self,key,None)
		if value is None:
			field=self.__mappings__[key]
			if field.default is not None:
				value=field.default() if callable(field.default) else field.default
				logging.debug('using default value for %s:%s'%(key,str(value)))
				setattr(self,key,value)
		return value
	
#---每个Model类的子类实例应该具备的执行SQL的方法比如save---	
	@classmethod	#类方法
	@asyncio.coroutine
	def findAll(cls,where=None,args=None,**kw):
		'''
			cls:类方法的self
			where:sql where
			args:参数
			**kw:你想指定的sql参数{orderBy:way...}
		'''
		sql=[cls.__select__]	
		if where:
			sql.append('where')
			sql.append(where)
		if args is None:
			args=[]
		orderBy=kw.get('orderBy',None)
		if orderBy:
			sql.append('order by')
			sql.append(orderBy)
		limit=kw.get('limit',None)
		if limit is not None:
			sql.append('limit')
			if isinstance(limit,int):
				sql.append('?')
				args.append(limit)
			elif isinstance(limit,tuple) and len(limit)==2:
				sql.append('?,?')
				args.extend(limit)
			else:
				raise ValueError('Invaild limit value:%s'% str(limit))
		rs=yield from select(' '.join(sql),args)
		return [cls(**r) for r in rs]

	@classmethod	#类方法	
	@asyncio.coroutine
	def findNumber(cls,selectField,where=None,args=None):
		'''find number by select and where
			cls:类名
			selectField:select的属性
			where:where='where attrt=xxxx'
			args:属性参数
		'''
		sql=['select %s _num_ from `%s`'% (selectField,cls.__table__)]
		if where:
			sql.append('where')
			sql.append(where)
		rs=yield from select(' '.join(sql),args,1)
		if len(rs)==0:
			return None
		return rs[0]['_num_']

	@classmethod
	@asyncio.coroutine
	def  find(cls,pk):
		'''
			cls：类名
			pk:primary_key
		'''
		'find object by primary_key'
		rs=yield from select('%s where `%s`=?'% (cls.__select__,cls.__primary_key__),[pk],1)
		if len(rs)==0:
			return None
		return cls(**rs[0])

	#实例方法
	@asyncio.coroutine
	def save(self):
		args=list(map(self.getValueOrDefault,self.__fields__))
		args.append(self.getValueOrDefault(self.__primary_key__))
		rows=yield from execute(self.__insert__,args)
		if rows !=1:
			logging.warn('failed to insert record:affected rows:%s'% rows)

	@asyncio.coroutine
	def update(self):
		args=list(map(self.getValue,self.__fields__))
		args.append(self.getValue(self.__primary_key__))
		rows=yield from execute(self.__update__,args)
		print(self.__update__,args)
		if rows !=1:
			logging.warn('failed to update by primary key:affected rows %s'% rows)
	
	@asyncio.coroutine
	def remove(self):
		args=[self.getValue(self.__primary_key__)]
		rows=yield from execute(self.__delete__,args)
		if rows!=1:
			logging.warn('failed to remove by primary  key:affected rows %s'% rows)

if __name__=='__mian__':
	print('webapp-------------------------->test------------------------------->')
	
