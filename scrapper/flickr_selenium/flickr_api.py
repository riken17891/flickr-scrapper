import asyncio
import json
import logging

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

logging.basicConfig(level=logging.INFO, filename=FLICKR_API["log"])
logger = logging.getLogger(__name__)


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
    def post(self, city):
        city = city.lower()

        result = {}
        if city in current_requests:
            logging.info("Duplicate Search for : {} ".format(city))
            result["result"] = "Duplicate Search for : {} ".format(city)
            self.write(result)
            self.flush()
            return
        else:
            logging.info("Started Search for : {} ".format(city))
            result["result"] = "Started Search for : {} ".format(city)
            self.write(result)
            self.flush()
            current_requests.append(city)

        image_links_queue = asyncio.Queue(loop=loop)
        geo_model_queue = asyncio.Queue(loop=loop)

        # get all image links and put it to image_links_queue
        task1 = loop.create_task(self.geo_model_consumer(city=city, geo_model_queue=geo_model_queue))
        # get each image link from image_links_queue,
        # open it,
        # retrieve geo model from page source,
        # put it to geo_model_queue
        task2 = loop.create_task(self.geo_model_producer(city=city, image_links_queue=image_links_queue,
                                                         geo_model_queue=geo_model_queue))
        # send geo model as post data to centralized database operations api
        task3 = loop.create_task(self.image_link_producer(city=city, image_links_queue=image_links_queue))

        asyncio.gather(task1, task2, task3)

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

                logging.info("Reading : {} : {}".format(city, link))

                yield from self.bound_read_one(city=city, url=link, session=session, result_queue=geo_model_queue)

                image_links_queue.task_done()

    @asyncio.coroutine
    def geo_model_consumer(self, city, geo_model_queue):
        with aiohttp.ClientSession(loop=loop) as session:
            url = "http://{}:{}{}".format(DB_API["host"], DB_API["port"], DB_API["geo_path"])
            while True:
                model = yield from geo_model_queue.get()

                logging.info("Posting : {} : {} ".format(city, json.dumps(model)))

                if model is not None and model:
                    yield from self.post_one(url=url, session=session,
                                             data=json.dumps([model], sort_keys=True))

                geo_model_queue.task_done()

    @staticmethod
    async def post_one(url, session, data):
        async with session.post(url, data=data) as response:
            logging.info("Finished Posting : {} : {} ".format(data, str(response.status)))

    @staticmethod
    async def read_one(city, url, session, result_queue):
        try:
            async with session.get(url=url) as response:
                if response.status == 200:
                    page_content = await response.read()
                    logging.info("Finished Reading : {} ".format(url))
                    await result_queue.put(FlickrImagePage(page_content).get_geo_model(city=city, url=url))
        except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError,
                aiohttp.ClientConnectorCertificateError,
                aiohttp.ServerDisconnectedError,
                aiohttp.ClientSSLError,
                aiohttp.ClientResponseError,
                asyncio.TimeoutError,
                TimeoutError) as e:
            logging.error("Error Reading : {} : {} ".format(url, e))

    async def bound_read_one(self, city, url, session, result_queue):
        async with semaphore:
            await self.read_one(city, url, session, result_queue)


def flickr_search_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/start/search/(.*)", SearchHandler)
    ])

if __name__ == "__main__":
    AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()
    semaphore = asyncio.Semaphore(100)

    current_requests = []

    app = flickr_search_app()
    app.listen(FLICKR_API["port"])
    logging.info("Application started at port {}".format(FLICKR_API["port"]))
    loop.run_forever()
