# -*- coding: utf-8 -*-
from __future__ import absolute_import
import logging
import collections

from twisted.internet.defer import Deferred
from scrapy import signals


logger = logging.getLogger(__name__)


def scrape_items(crawler_runner, crawler_or_spidercls, *args, **kwargs):
    """
    Start a crawl and return an object (ItemCursor instance)
    which allows to retrieve scraped items and wait for items
    to become available.

    Example:

    .. code-block:: python

        @inlineCallbacks
        def f():
            runner = CrawlerRunner()
            async_items = scrape_items(runner, my_spider)
            while (yield async_items.fetch_next):
                item = async_items.next_item()
                # ...
            # ...

    This convoluted way to write a loop should become unnecessary
    in Python 3.5 because of ``async for``.
    """
    crawler = crawler_runner.create_crawler(crawler_or_spidercls)
    d = crawler_runner.crawl(crawler, *args, **kwargs)
    return ItemCursor(d, crawler)


class ItemCursor(object):
    def __init__(self, crawl_d, crawler):
        self.crawl_d = crawl_d
        self.crawler = crawler

        crawler.signals.connect(self._on_item_scraped, signals.item_scraped)
        crawler.signals.connect(self._on_error, signals.spider_error)

        crawl_d.addCallback(self._on_finished)
        crawl_d.addErrback(self._on_error)

        self.closed = False
        self._items_available = Deferred()
        self._items = collections.deque()

    def _on_item_scraped(self, item):
        # logger.info("_on_item_scraped")
        self._items.append(item)
        self._items_available.callback(True)
        self._items_available = Deferred()

    def _on_finished(self, result):
        # logger.info("_on_finished")
        self.closed = True
        self._items_available.callback(False)

    def _on_error(self, failure):
        self.closed = True
        self._items_available.errback(failure)

    @property
    def fetch_next(self):
        """
        A Deferred used with ``inlineCallbacks`` or ``gen.coroutine`` to
        asynchronously retrieve the next item, waiting for an item to be
        crawled if necessary. Resolves to ``False`` if the crawl is finished,
        otherwise :meth:`next_item` is guaranteed to return an item
        (a dict or a scrapy.Item instance).
        """
        if self.closed:
            # crawl is finished
            d = Deferred()
            d.callback(False)
            # logger.info("fetch_next: crawl is finished")
            return d

        if self._items:
            # result is ready
            d = Deferred()
            d.callback(True)
            # logger.info("fetch_next: result is ready")
            return d

        # We're active, but item is not ready yet. Return a Deferred which
        # resolves to True if item is scraped or to False if crawl is stopped.
        # logger.info("fetch_next: active, but items are not ready")
        return self._items_available

    def next_item(self):
        """Get a document from the most recently fetched batch, or ``None``.
        See :attr:`fetch_next`.
        """
        if not self._items:
            # logger.info("no next_item")
            return None
        # logger.info("got next_item")
        return self._items.popleft()
