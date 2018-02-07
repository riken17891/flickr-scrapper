import asyncio
import json

import aiohttp
import tornado.escape
import tornado.ioloop
import tornado.web
from tornado import gen
from tornado.platform.asyncio import AsyncIOMainLoop

from selenium.selenium_api import FlickrImagePage
from selenium.selenium_api import FlickrSearch

from config import FLICKR_API
from config import DB_API


class MainHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    @gen.coroutine
    def get(self):
        self.write("Ok!")


class SearchHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    @gen.coroutine
    def get(self, city):
        image_links_queue = asyncio.Queue(loop=loop, maxsize=20)
        geo_model_queue = asyncio.Queue(loop=loop, maxsize=20)

        loop.create_task(self.geo_model_consumer(city=city, geo_model_queue=geo_model_queue))
        loop.create_task(self.geo_model_producer(city=city, image_links_queue=image_links_queue,
                                                 geo_model_queue=geo_model_queue))
        loop.create_task(self.image_link_producer(city=city, image_links_queue=image_links_queue))

        yield image_links_queue.join()
        yield geo_model_queue.join()

    @asyncio.coroutine
    def image_link_producer(self, city, image_links_queue):
        flickr_search = FlickrSearch(city)
        yield from flickr_search.get_all_images(image_links_queue)

    @asyncio.coroutine
    def geo_model_producer(self, city, image_links_queue, geo_model_queue):
        with aiohttp.ClientSession(loop=loop) as session:
            while True:
                link = yield from image_links_queue.get()
                print("{} : {}".format(city, link))

                if link is None:
                    break

                asyncio.ensure_future(read_one(url=link, session=session, result_queue=geo_model_queue))

    @asyncio.coroutine
    def geo_model_consumer(self, city, geo_model_queue):
        models = []

        with aiohttp.ClientSession(loop=loop) as session:
            url = "http://{}:{}{}".format(DB_API["host"], DB_API["port"], DB_API["geo_path"])
            while True:
                model = yield from geo_model_queue.get()
                print("{} : {}".format(city, json.dumps(model)))

                if model is None:
                    asyncio.ensure_future(post_one(url=url, session=session,
                                                   data=json.dumps(models, sort_keys=True)))
                    break

                if model is not None and model:
                    models.append(model[0])

                if len(models) == 25:
                    asyncio.ensure_future(post_one(url=url, session=session,
                                                   data=json.dumps(models, sort_keys=True)))
                    models = []

async def post_one(url, session, data):
    async with session.post(url, data=data) as response:
        print(response.status)

async def read_one(url, session, result_queue):
    async with session.get(url=url) as response:
        page_content = await response.read()
        await result_queue.put(FlickrImagePage(page_content).get_geo_model())


def flickr_search_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/start/search/(.*)", SearchHandler)
    ])

if __name__ == "__main__":
    AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()

    app = flickr_search_app()
    app.listen(FLICKR_API["port"])
    print("Application started at port {}".format(FLICKR_API["port"]))
    loop.run_forever()
