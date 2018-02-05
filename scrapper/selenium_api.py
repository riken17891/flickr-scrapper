import time
import queue
import threading
import requests
import aiohttp
import asyncio
import re
import json

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup


class FlickrSearch:

    picture_link_selector = "div.photo-list-photo-interaction a.overlay"
    load_more_selector = ".infinite-scroll-load-more button"

    def __init__(self, place):
        options = webdriver.ChromeOptions()
        #options.add_argument('headless')

        self.browser = webdriver.Chrome(chrome_options=options)
        self.open("https://www.flickr.com/search/?text={0}".format(place))

        self.page_link_queue = queue.Queue()
        self.image_geo_model_queue = queue.Queue()

    def open(self, url):
        self.browser.get(url)

    def get_title(self):
        return self.browser.title

    def get_and_process_each_image(self):
        process_link_threads = []
        for w in range(8):
            process_link_thread = threading.Thread(target=self.open_link_and_collect_gps_data,
                                                   name='open_link_and_collect_gps_data-%s' % w)
            process_link_thread.daemon = True
            process_link_thread.start()
            print("started : " + process_link_thread.name)
            process_link_threads.append(process_link_thread)

        add_link_thread = threading.Thread(target=self.scroll_to_bottom_until_no_load_more_and_add_links_to_queue,
                                           name='get_link_and_to_queue')
        add_link_thread.daemon = True
        add_link_thread.start()
        print("started : " + add_link_thread.name)

        add_link_thread.join()
        self.page_link_queue.join()

    def open_link_and_collect_gps_data(self):
        while True:
            if not self.page_link_queue.empty():
                link = self.page_link_queue.get()

                image_page = FlickrImagePage(link)

                geo_model = image_page.get_geo_model()
                print(link)
                print(geo_model)

                self.image_geo_model_queue.put(geo_model)

                self.page_link_queue.task_done()

    def scroll_to_bottom_until_no_load_more_and_add_links_to_queue(self):
        last_height = self.scroll_height()
        start = 0
        total = 0

        while True:
            self.scroll_to_bottom()
            time.sleep(2)

            new_height = self.scroll_height()

            if new_height == last_height and not(self.check_and_click_if_load_more_exists()):
                time.sleep(10)

                if not(self.check_and_click_if_load_more_exists()):
                    break

            links = self.get_all_image_links_incrementally(start)
            list(map(lambda element: self.page_link_queue.put(element.get_attribute("href")), links))

            print("Incremental : ", len(links))

            last_height = new_height
            total = total + len(links)
            start = total

    def scroll_to_bottom(self):
        self.browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_height(self):
        return self.browser.execute_script("return document.body.scrollHeight")

    def check_and_click_if_load_more_exists(self):
        try:
            load_more_button = self.browser.find_element_by_css_selector(self.load_more_selector)

            if load_more_button is not None:
                load_more_button.click()
                time.sleep(2)
                return True
        except NoSuchElementException:
            return False

    def get_all_image_links_incrementally(self, start=0):
        return self.get_all_elements_incrementally(self.browser, self.picture_link_selector, start)

    @staticmethod
    def get_all_elements_incrementally(driver, selector, start=0):
        return driver.execute_script("return Array.prototype.slice.call(document.querySelectorAll('{0}'), {1});"
                                     .format(selector, start))

    def close(self):
        self.browser.close()


class FlickrImagePage:

    soup = None
    model = None

    def __init__(self, url):
        self.read_url(url)

    async def read_url(self, url):
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                resp = await resp.text()
                self.soup = BeautifulSoup(resp)
                self.model = self.fetch_model(self.soup)

    @staticmethod
    def fetch_model(soup):
        script_tag = soup.select("script.modelExport")[0]
        script_content = script_tag.get_text()

        pattern = re.compile("modelExport: ({.*})")
        json_string = pattern.search(script_content).group(1)

        return json.loads(json_string)

    def get_geo_model(self):
        return self.model["main"]["photo-geo-models"]

flickr_search = FlickrSearch("newyork")
flickr_search.get_and_process_each_image()
flickr_search.close()