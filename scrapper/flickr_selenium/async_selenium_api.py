from arsenic import get_session
from arsenic.errors import NoSuchElement
from arsenic.services import Chromedriver
from arsenic import browsers

import asyncio


class AsyncSelenium:

    def __init__(self, url):
        self.service = Chromedriver()
        #chromeOptions={"args": ["--headless", "--disable-gpu"]}
        self.browser = browsers.Chrome()
        self.url = url

    async def init_session(self):
        async with get_session(self.service, self.browser) as session:
            return await session.get(self.url)

    @staticmethod
    async def scroll_to_bottom(session):
        last_height = await AsyncSelenium.scroll_height(session)
        print("Last Height : {}",format(last_height))

        await session.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    @staticmethod
    async def scroll_height(session):
        return await session.execute_script("return document.body.scrollHeight")

    @staticmethod
    async def check_and_click_if_load_more_exists(session):
        try:
            load_more_button = await session.get_element(".infinite-scroll-load-more button")
            await load_more_button.click()
            return True
        except NoSuchElement:
            print(NoSuchElement)
            return False

    @staticmethod
    async def scroll_and_load_more(session):
        while True:
            await AsyncSelenium.scroll_to_bottom(session)

            if not(await AsyncSelenium.check_and_click_if_load_more_exists(session)):
                break

    @staticmethod
    async def get_elements(session, start=0):
        elements = await session\
            .execute_script("return Array.prototype.slice.call(document.querySelectorAll('{0}'), {1});"
                            .format("div.photo-list-photo-interaction a.overlay", start))

        for element in elements:
            print(element)

    async def collect_elements(self):
        tasks = []

        async with get_session(self.service, self.browser) as session:
            await session.get(self.url)
            #scroll_and_load_more_task = asyncio.ensure_future(AsyncSelenium.scroll_and_load_more(session))
            #tasks.append(scroll_and_load_more_task)

            get_elements_task = asyncio.ensure_future(AsyncSelenium.get_elements(session, 0))
            tasks.append(get_elements_task)

        responses = asyncio.gather(tasks)
        await responses


def main():
    loop = asyncio.get_event_loop()

    async_selenium = AsyncSelenium("https://www.flickr.com/search/?text=newyork")
    future = asyncio.ensure_future(async_selenium.collect_elements())
    loop.run_until_complete(future)

if __name__ == '__main__':
    main()
