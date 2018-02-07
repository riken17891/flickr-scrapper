import asyncio

import tornado.escape
import tornado.ioloop
import tornado.web
from tornado import gen
from tornado.platform.asyncio import AsyncIOMainLoop

from db.db_api import SqlLite
from config import FLICKR_DB


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

        geo_model_queue = asyncio.Queue(loop=loop, maxsize=100)

        asyncio.ensure_future(model_tuple_consumer(queue=geo_model_queue, sqlite=self.sqlite))
        asyncio.ensure_future(model_tuple_producer(queue=geo_model_queue, model=geo_model,
                                                   keys_to_keep=["id", "latitude", "longitude"]))

        yield geo_model_queue.join()


def flickr_search_app():
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/flicker/geo/", FlickrGeoInsertHandler, dict(sqlite=SqlLite(FLICKR_DB["db_name"])))
    ])


@asyncio.coroutine
def model_tuple_producer(queue, model, keys_to_keep):

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
        print(model_tuple)
        sqlite.execute_insert(FLICKR_DB["geo_insert_into_table_sql"].format(FLICKR_DB["geo_table_name"]), [model_tuple])

        queue.task_done()


if __name__ == "__main__":
    AsyncIOMainLoop().install()
    loop = asyncio.get_event_loop()

    app = flickr_search_app()
    app.listen(8889)
    print("Application started at port {}".format(8889))
    loop.run_forever()
