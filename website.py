#!/usr/bin/env python
# -*- coding:utf-8 -*-

from __future__ import division
import os
import logging
import time
import hashlib
import urlparse
from datetime import datetime, timedelta
from urllib import unquote, quote_plus

import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.autoreload
import tornado.httpclient
from tornado import locale
from tornado.options import define, options

from crawler import Book
from rules import rules

import celerytasks

define("port", default=8800, help="The port to be listened", type=int)
define("debug", default=False, help="debug mode", type=bool)

data_dir = os.path.join(os.path.dirname(__file__), 'data')

class Application(tornado.web.Application):
    def __init__(self):
        urls = [
            (r"/", HomeHandler),
            (r"/book/([a-z0-9]+)", BookHandler),
            (r"/book/([a-z0-9]+).(epub|mobi)", DownHandler),
        ]
        settings = dict(
            template_path = os.path.join(os.path.dirname(__file__), "views"),
            static_path = os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies = True,
            cookie_secret = "kL5gEmGeJJFuYh711oETzKXQAGaYdEQnp2XdTP1o/Vo=",
            debug = options.debug,
            login_url = "/login",
        )
        tornado.web.Application.__init__(self, urls, **settings)
        
class BaseHandler(tornado.web.RequestHandler):

    def is_url(self, url):
        """docstring for is_url"""
        pass
        

class HomeHandler(BaseHandler):
    """docstring for HomeHandler"""
    def get(self, error=None, url=None, book_id=None):
        """docstring for fname"""
        
        if url is None:
            url = self.get_argument("url", None)
        
        self.render("home.html", error = error, url=url, book_id=book_id)
        
        
    def post(self):
        """docstring for fname"""
        
        url = self.get_argument("url", None)
        
        if not url:
            self.get(2, url)
        elif not self.is_url(url):
            self.get(3, url)
        elif not in_rules(url):
            self.get(4, url)
        else:
            
            book = Book(url)
            if not book.is_exists:
                celerytasks.add_crawler.apply_async(args=[url]) #, eta=datetime.now() + timedelta(seconds=10))
                
            self.redirect('book/%s' % book.id)
            
class BookHandler(BaseHandler):
    """docstring for BookHandler"""
    
    def get(self, book_id):
        """docstring for get"""
        
        book = Book(id=book_id)
        self.render('down.html', is_ready=book.is_ready, book_id=book.id, epub=book.epub, mobi=book.mobi)
    
class DownHandler(BaseHandler):
    """docstring for DownHandler"""
    
    def get(self, book_id, filetype):
        
        mime_types = {
            'mobi':'application/x-mobipocket-ebook',
            'epub':'application/epub-zip'
        }
        
        book = Book(id=book_id)
        
        if filetype is 'epub':
            book_file = book.epub
        else:
            book_file = book.mobi
            
        fp = open(book_file, 'r')
        data = fp.read()
        fp.close()
        
        self.set_header("Content-Type", mime_types[filetype])
        self.set_header("Content-Length", len(data))
        self.set_header("Content-Disposition", 'attachment; filename="%s.%s"' % (book_id, filetype))
        self.set_header("Cache-Control", "private, max-age=0, must-revalidate")
        self.set_header("Pragma", "public")
        self.write(data)

def runserver():
    tornado.options.parse_command_line()
    
    http_server = tornado.httpserver.HTTPServer(Application())
    
    if options.debug:
        http_server.listen(options.port)
    else:
        http_server.bind(options.port)
        http_server.start(6)

    tornado.ioloop.IOLoop.instance().start()
    
if __name__ == "__main__":
    runserver()