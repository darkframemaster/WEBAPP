#!/usr/bin/env python3
#-*- coding:utf-8 -*-

import orm 
from models import User,Blog,Comment
import asyncio
import time

#实例测式
@asyncio.coroutine
def test(loop):
	yield from orm.create_pool(loop,user='root',password='xh1008',db='darkframexue')
	u=User(name='zhiling',email='test1@example.com',password='1234567890',image='about:blank')	
	yield from u.save()

@asyncio.coroutine
def test_remove(loop):
	yield from orm.create_pool(loop,user='root',password='xh1008',db='darkframexue')
	u=User(id='0014594260710686cff1d482ef749bdb195f5b335043c38000')
	yield from u.remove()
	
@asyncio.coroutine
def test_update(loop):
	yield from orm.create_pool(loop,user='root',password='xh1008',db='darkframexue')
	# primary_key必须和数据库一直，其他属性可以设置成新的值,属性要全
	u=User(id='001459426692207a6e158deda1f4963aa961653a13b5d9e000',
	create_at=time.time(),
	password='test',
	image='about:blank',
	admin=True,
	name='xiaobo',
	email='hello1@example.com')
	yield from u.update()
	

#类测试
@asyncio.coroutine
def test_findAll(loop):
	yield from orm.create_pool(loop,user='root',password='xh1008',db='darkframexue')
	rs=yield from User.findAll(email='test@example.com')
	for i in range(len(rs)):
		print(rs[i])

@asyncio.coroutine
def test_findNumber(loop):
	yield from orm.create_pool(loop,user='root',password='xh1008',db='darkframexue')
	count=yield from User.findNumber('email')
	print(count)

@asyncio.coroutine
def test_find_by_key(loop):
	yield from orm.create_pool(loop,user='root',password='xh1008',db='darkframexue')
	rs=yield from User.find('0014594162769468118a9a064894773b8fdec63ffc3a5a3000')
	print(rs)

loop=asyncio.get_event_loop()
loop.run_until_complete(test_update(loop))
__pool=orm.__pool
__pool.close()
loop.run_until_complete(__pool.wait_closed())
loop.close()


