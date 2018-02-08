import asyncio
import logging

import tornado.escape
import tornado.ioloop
import tornado.web
from tornado import gen
from tornado.platform.asyncio import AsyncIOMainLoop

from db.db_api import SqlLite
from config import FLICKR_DB
from config import DB_API

logging.basicConfig(level=logging.INFO, filename=DB_API["log"])
logger = logging.getLogger(__name__)


class MainHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    @gen.coroutine
    def get(self):
        self.write("Ok!")


class FlickrGeoInsertHandler(tornado.web.RequestHandler):
    def initialize(self, sqlite):
        self.sqlite = sqlite
        self.sqlite.execute(FLICKR_DB["geo_create_table_sql"].format(FLICKR_DB["geo_table_name"]))

    def data_received(self, chunk):
        pass

    @gen.coroutine
    def get(self):
        rows = self.sqlite.execute_select(FLICKR_DB["geo_select_all_sql"].format(FLICKR_DB["geo_table_name"]))
        self.write({"result": rows})

    @gen.coroutine
    def post(self):
        geo_model = tornado.escape.json_decode(self.request.body)

        geo_model_queue = asyncio.Queue(loop=loop)

        # generate tuples from json payload and add to geo_model_queue
        task1 = loop.create_task(model_tuple_consumer(queue=geo_model_queue, sqlite=self.sqlite))
        # insert tuples to database
        task2 = loop.create_task(model_tuple_producer(queue=geo_model_queue, model=geo_model,
                                                      keys_to_keep=DB_API["geo_fields"]))

        asyncio.gather(task1, task2)

        yield geo_model_queue.join()


def flickr_search_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/flickr/geo/", FlickrGeoInsertHandler, dict(sqlite=SqlLite(FLICKR_DB["db_name"])))
    ])


@asyncio.coroutine
def model_tuple_producer(queue, model, keys_to_keep):
        # filter models to keep only keys provides using keys_to_keep
        for m in model:
            keys = m.keys()

            for key in list(keys):
                if key not in keys_to_keep:
                    m.pop(key, None)

            yield from queue.put(tuple(m.values()))


@asyncio.coroutine
def model_tuple_consumer(queue, sqlite):
    while True:
        model_tuple = yield from queue.get()
        logging.info("Added : {}".format(model_tuple))
        sqlite.execute_insert(FLICKR_DB["geo_insert_into_table_sql"].format(FLICKR_DB["geo_table_name"]), [model_tuple])

        queue.task_done()


if __name__ == "__main__":
    AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()

    app = flickr_search_app()
    app.listen(DB_API["port"])
    logging.info("Application started at port {}".format(DB_API["port"]))
    loop.run_forever()
