#!/usr/bin/env python3
#-*- coding:utf-8 -*-

__author__='xuehao'

import re,time,json,logging,hashlib,base64,asyncio

from aiohttp import web

from webFrame import get,post
from apis import *	#APIValueError,APIResourceNotFoundError,APIError,Page

from models import User,Comment,Blog,next_id
from config import configs

import markdown2

COOKIE_NAME='darksession'
_COOKIE_KEY=configs.session.secret

'''
 该脚本的@get&@post函数会被注册到app的路由器中
 在客户端请求时，返回网页端的请求
'''




def user2cookie(user,max_age):
	#build cookie string by:id-expires-sha1
	expires=str(int(time.time()+max_age))
	s='%s-%s-%s-%s'%(user.id,user.password,expires,_COOKIE_KEY)
	L=[user.id,expires,hashlib.sha1(s.encode('utf-8')).hexdigest()]
	return '-'.join(L)


@asyncio.coroutine
def cookie2user(cookie_str):
	'''
	Parse cookie and load user if cookie is valid.
	'''
	if not cookie_str:
		return None
	try:
		L=cookie_str.split('-')
		if len(L)!=3:
			return None
		uid,expires,sha1=L
		if int(expires)<time.time():
			return None
		user=yield from User.find(uid)
		if user is None:
			return None
		s='%s-%s-%s-%s'%(uid,user.password,expires,_COOKIE_KEY)
		if sha1!=hashlib.sha1(s.encode('utf-8')).hexdigest():
			logging.info('invalid sha1')
			return None
		user.password='******'
		return user
	except Exception as e:
		logging.exception(e)
		return None

def check_admin(request):
	if request.__user__ is None or request.__user__.admin:
		raise APIPermissionError('user admin')

def get_page_index(page_str):
	p=1	
	try:
		p=int(page_str)
	except ValueError as e:
		pass
	if p<1:
		p=1
	return p

def text2html(text):
	lines=map(lambda s: '<p>%s</p>'% s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;'),filter(lambda s:s.strip()!='',text.split('\n')))
	return ''.join(lines)

#home页面
#url处理函数,get('/')添加path and method
@get('/')
@asyncio.coroutine
def index(*,page='1'):
	page_index=get_page_index(page)
	num=yield from Blog.findNumber('count(id)')
	page=Page(num)
	if num==0:
		blogs=[]
	else:
		blogs=yield from Blog.findAll(orderBy='create_at desc',limit=(page.offset,page.limit))
	return {
        '__template__': 'blogs.html',
        'blogs': blogs,
	'page':page
    }

#注册页面
@get('/register')
def register():
	return{
		'__template__':'register.html'	
	}

#登录页面
@get('/signin')
def signin():
	return{
		'__template__':'signin.html'
	}

	
@get('/signout')
def signout(request):
	referer=request.headers.get('Referer')
	r=web.HTTPFound(referer or '/')
	r.set_cookie(COOKIE_NAME,'-deleted-',max_age=0,httponly=True)
	logging.info('user signed out.')
	return r

#blog页面
@get('/blog/{id}')
def get_blog(id):
	blog=yield from Blog.find(id)
	comments=yield from Comment.findAll('blog_id=?',[id],orderBy='create_at desc')
	for c in comments:
		c.html_content=text2html(c.content)
	blog.html_content=markdown2.markdown(blog.content)
	return {
	'__template__':'blog.html',
	'blog':blog,
	'comments':comments
	}


'''
	manage:管理页面

'''
@get('/manage')
def manage():
	return 'redirect:/manage/comments'

@get('/manage/comments')
def manage_comments(*,page='1'):
	return {
	'__template__':'manage_comments.html',
	'page_index':get_page_index(page)
	}

#blog 列表
@get('/manage/blogs')
def manage_blogs(*,page='1'):
	return {
	'__template__':'manage_blogs.html',
	'page_index':get_page_index(page)
	}

#create blog页面
@get('/manage/blogs/create')
def manage_create_blog():
	return {
	'__template__':'manage_blog_edit.html',
	'id':'',
	'action':'/api/blogs'
	}

#编辑页面
@get('/manage/blogs/edit')
def manage_edit_blog(*,id):
	return{
	'__template__':'manage_blog_edit.html',
	'id':id,
	'action':'/api/blogs/%s'%id	
	}

@get('/manage/users')
def manage_users(*,page='1'):
	return{
	'__template__':'manage_users.html',
	'page_index':get_page_index(page)
	}




'''
	API

'''
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$')
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$')


'''
	comments API
'''
@get('/api/comments')
def api_comments(*,page='1'):
	page_index=get_page_index(page)
	num=yield from Comment.findNumber('count(id)')
	p=Page(num,page_index)
	if num==0:
		return dict(page=p,comments=())
	comments=yield from Comment.findAll(orderBy='create_at desc',limit=(p.offset,p.limit))
	return dict(page=p,comments=comments)	

@get('/api/blogs/{id}/comments')
def api_create_comment(id,request,*,content):
	user=request.__user__
	if user is None:
		raise APIPermissonError('Please signin first.')
	if not content or not content.strip():
		raise APIValueError('content')
	blog =yield from Blog.find(id)
	if blog is None:
		raise APIResourceNotFoundError('Blog')
	comment =Comment(blog_id=blog.id,user_id=user.id,user_name=user.name,user_image=user.image,content=content.strip())
	yield from comment.save()
	return comment

@post('/api/comments/{id}/delete')
def api_delete_comments(id,request):
	check_admin(request)
	c=yield from Comment.find(id)
	if c is None:
		raise APIResourceNotFoundError('Comment')
	yield from c.remove()
	return dict(id=id)

'''
	blogs API
'''
@get('/api/blogs/{id}')
def api_get_blog(*,id):
	blog=yield from Blog.find(id)
	return blog

@get('/api/blogs')
def api_blogs(*,page='1'):
	page_index=get_page_index(page)
	num=yield from Blog.findNumber('count(id)')
	p=Page(num,page_index)
	if num==0:
		return dict(page=p,blogs=())
	blogs=yield from Blog.findAll(orderBy='create_at desc',limit=(p.offset,p.limit))
	return dict(page=p,blogs=blogs)

@post('/api/blogs')
def api_create_blog(request,*,name,summary,content):
	check_admin(request)
	if not name or not name.strip():
		raise APIValueError('name','name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary','summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content','content cannot be empty.')
	blog=Blog(user_id=request.__user__.id,user_name=request.__user__.name,user_image=request.__user__.image,name=name.strip(),summary=summary.strip(),content=content.strip())
	yield from blog.save()
	return blog

@post('/api/blogs/{id}/delete')
def api_delete_blog(request,*,id):
	check_admin(request)
	blog=yield from Blog.find(id)
	yield from blog.remove()
	return dict(id=id)

@post('/api/blogs/{id}')
def api_update_blog(id,request,*,name,summary,content):
	check_admin(request)
	blog=yield from Blog.find(id)
	if not name or not name.strip():
		raise APIValueError('name','name cannot be empty.')
	if not summary or not summary.strip():
		raise APIValueError('summary','summary cannot be empty.')
	if not content or not content.strip():
		raise APIValueError('content','content cannot be empty.')
	blog.name=name.strip()
	blog.summary=summary.strip()
	blog.content=content.strip()
	yield from blog.update()
	return blog


@get('/api/users')
def api_get_users(*,page='1'):
	page_index=get_page_index(page)
	num=yield from User.findNumber('count(id)')
	p=Page(num,page_index)
	if num==0:
		return dict(page=p,users=())
	users=yield from User.findAll(orderBy='create_at desc',limit=(p.offset,p.limit))
	for u in users:
		u.password='******'
	return dict(page=p,users=users)



@post('/api/users')
def api_register_user(*,email,name,passwd):
	if not name or not name.strip():
		raise APIValueError('name')
	if not email or not _RE_EMAIL.match(email):
		raise APIValueError('email')
	if not passwd or not _RE_SHA1.match(passwd):
		raise APIValueError('passwd')
	user=yield from User.findAll('email=?',[email])
	if len(user)>0:
		raise APIError('register:failed','email','Email is already in use.')
	uid =next_id()
	sha1_passwd='%s:%s'%(uid,passwd)
	user=User(id=uid,name=name.strip(),email=email,password=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(),image='http://www.gravatar.com/avatar/%s?d=mm&s=120'%hashlib.md5(email.encode('utf-8')).hexdigest())
	yield from user.save()
	
	r=web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
	user.passwd='******'
	r.content_type='application/json'
	r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
	return r


@post('/api/authenticate')
def authenticate(*,email,passwd):
	if not email:
		raise APIValueError('email','Invalid email.')
	if not passwd:
		raise APIValueError('passwd','Invalid passwd.')
	users=yield from User.findAll('email=?',[email])
	if len(users)==0:
		raise APIValueError('email','Email not exist.')
	user=users[0]
	#check passwd:
	sha1=hashlib.sha1()
	sha1.update(user.id.encode('utf-8'))
	sha1.update(b':')
	sha1.update(passwd.encode('utf-8'))
	if user.password!=sha1.hexdigest():
		raise APIValueError('passwd','Invalid password.')
	#authenticate ok,set cookie:
	r=web.Response()
	r.set_cookie(COOKIE_NAME,user2cookie(user,86400),max_age=86400,httponly=True)
	user.passwd='******'
	r.content_type='application/json'
	r.body=json.dumps(user,ensure_ascii=False).encode('utf-8')
	return r



