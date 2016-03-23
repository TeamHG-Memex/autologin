# -*- coding: utf-8 -*-
from __future__ import absolute_import  
from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
from scrapy.http.cookies import CookieJar


class ExposeCookiesMiddleware(CookiesMiddleware):
    """
    This middleware appends CookieJar with current cookies to response flags.

    To use it, disable default CookiesMiddleware and enable
    this middleware instead::

        DOWNLOADER_MIDDLEWARES = {
            'scrapy.downloadermiddlewares.cookies.CookiesMiddleware': None,
            'autologin.middleware.ExposeCookiesMiddleware': 700,
        }

    """
    def process_response(self, request, response, spider):
        response = super(ExposeCookiesMiddleware, self).process_response(
            request, response, spider)
        cookiejarkey = request.meta.get("cookiejar")
        response.flags.append(self.jars[cookiejarkey])
        return response


def get_cookiejar(response):
    for obj in response.flags:
        if isinstance(obj, CookieJar):
            return obj
