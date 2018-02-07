import asyncio
import json

import aiohttp
import tornado.escape
import tornado.ioloop
import tornado.web
from tornado import gen
from tornado.platform.asyncio import AsyncIOMainLoop

from flickr_selenium.selenium_api import FlickrImagePage
from flickr_selenium.selenium_api import FlickrSearch

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
        image_links_queue = asyncio.Queue(loop=loop)
        geo_model_queue = asyncio.Queue(loop=loop)

        task1 = loop.create_task(self.geo_model_consumer(city=city, geo_model_queue=geo_model_queue))
        task2 = loop.create_task(self.geo_model_producer(city=city, image_links_queue=image_links_queue,
                                                         geo_model_queue=geo_model_queue))
        task3 = loop.create_task(self.image_link_producer(city=city, image_links_queue=image_links_queue))

        asyncio.gather(task1, task2, task3)

        yield image_links_queue.join()
        yield geo_model_queue.join()

    @asyncio.coroutine
    def image_link_producer(self, city, image_links_queue):
        print("Started Search for : ", city)
        flickr_search = FlickrSearch(city)
        yield from flickr_search.get_all_images(image_links_queue)

    @asyncio.coroutine
    def geo_model_producer(self, city, image_links_queue, geo_model_queue):
        with aiohttp.ClientSession(loop=loop) as session:
            while True:
                link = yield from image_links_queue.get()

                print("Reading : ", city, link)

                yield from self.bound_read_one(url=link, session=session, result_queue=geo_model_queue)

                image_links_queue.task_done()

    @asyncio.coroutine
    def geo_model_consumer(self, city, geo_model_queue):
        with aiohttp.ClientSession(loop=loop) as session:
            url = "http://{}:{}{}".format(DB_API["host"], DB_API["port"], DB_API["geo_path"])
            while True:
                model = yield from geo_model_queue.get()

                print("Posting : ", city, json.dumps(model))

                if model is not None and model:
                    yield from self.post_one(url=url, session=session,
                                             data=json.dumps([model[0]], sort_keys=True))

                geo_model_queue.task_done()

    @staticmethod
    async def post_one(url, session, data):
        async with session.post(url, data=data) as response:
            print("Finished Posting :", data, str(response.status))

    @staticmethod
    async def read_one(url, session, result_queue):
        try:
            async with session.get(url=url) as response:
                if response.status == 200:
                    page_content = await response.read()
                    print("Finished Reading : " + url)
                    await result_queue.put(FlickrImagePage(page_content).get_geo_model())
        except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError,
                aiohttp.ClientConnectorCertificateError,
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientSSLError,
                aiohttp.ClientResponseError,
                asyncio.TimeoutError,
                TimeoutError) as e:
            print("Error Reading : ", url, e)

    async def bound_read_one(self, url, session, result_queue):
        async with semaphore:
            await self.read_one(url, session, result_queue)


def flickr_search_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/start/search/(.*)", SearchHandler)
    ])

if __name__ == "__main__":
    AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(100)

    app = flickr_search_app()
    app.listen(FLICKR_API["port"])
    print("Application started at port {}".format(FLICKR_API["port"]))
    loop.run_forever()
