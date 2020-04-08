# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class TauntondeedsparserItem(scrapy.Item):
    date = scrapy.Field()
    type_ = scrapy.Field()
    book = scrapy.Field()
    page_num = scrapy.Field()
    doc_num = scrapy.Field()
    city = scrapy.Field()
    description = scrapy.Field()
    cost = scrapy.Field()
    street_address = scrapy.Field()
    state = scrapy.Field()
    zip_ = scrapy.Field()
