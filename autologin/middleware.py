# -*- coding: utf-8 -*-
from __future__ import absolute_import

from scrapy.http.cookies import CookieJar
from scrapy.downloadermiddlewares.cookies import CookiesMiddleware
from scrapy.downloadermiddlewares.httpproxy import HttpProxyMiddleware
from scrapy.exceptions import NotConfigured


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


class ProxyFromSettingsMiddleware(HttpProxyMiddleware):
    """A middleware that sets proxy from settings file"""

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def __init__(self, settings):
        self.proxies = {}
        proxies = [
            ('http', settings.get('HTTP_PROXY')),
            ('https', settings.get('HTTPS_PROXY')),
        ]
        for type_, url in proxies:
            if url:
                self.proxies[type_] = self._get_proxy(url, type_)
        if not self.proxies:
            raise NotConfigured
