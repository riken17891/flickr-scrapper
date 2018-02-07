import re
import json

import asyncio

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

from config import FLICKR_SEARCH
from config import SELENIUM


class FlickrSearch:

    def __init__(self, place):
        options = webdriver.ChromeOptions()
        #options.add_argument('headless')

        self.place = place
        self.browser = webdriver.Chrome(chrome_options=options)
        self.open(FLICKR_SEARCH["url"].format(place))

    def open(self, url):
        self.browser.get(url)

    def get_title(self):
        return self.browser.title

    @asyncio.coroutine
    def get_all_images(self, queue):
        last_end = 0
        self.scroll_to_bottom()

        while True:
            links = self.get_all_image_links(start=last_end)

            for element in links:
                yield from queue.put(element.get_attribute("href"))

            if len(links) == 0:
                yield from queue.put(None)
                break

            last_end += len(links)

            for _ in range(5):
                if self.check_and_click_if_load_more_exists() or self.scroll_to_bottom():
                    yield from asyncio.sleep(5)

    def scroll_to_bottom(self):
        self.browser.execute_script(SELENIUM["scroll_to_bottom_script"])
        return True

    def scroll_height(self):
        return self.browser.execute_script(SELENIUM["scroll_height_script"])

    def check_and_click_if_load_more_exists(self):
        try:
            load_more_button = self.browser.find_element_by_css_selector(FLICKR_SEARCH["load_more_selector"])
            load_more_button.click()
            return True
        except NoSuchElementException:
            return False

    def get_all_image_links(self, start=0):
        links = self.get_all_elements(self.browser, FLICKR_SEARCH["picture_link_selector"], start)
        return links

    @staticmethod
    def get_all_elements(driver, selector, start=0):
        return driver.execute_script(SELENIUM["slice_array_script"].format(selector, start))

    def close(self):
        self.browser.close()


class FlickrImagePage:

    def __init__(self, page_content):
        self.soup = BeautifulSoup(page_content, "html5lib")
        self.model = self.fetch_model(self.soup)

    @staticmethod
    def fetch_model(soup):
        script_tag = soup.select_one(FLICKR_SEARCH["model_export_selector"])

        if script_tag is None:
            return {}

        script_content = script_tag.get_text()

        pattern = re.compile(FLICKR_SEARCH["model_export_pattern"])
        json_string = pattern.search(script_content).group(1)

        return json.loads(json_string)

    def get_geo_model(self):
        if not self.model:
            return []

        geo_model = self.model[FLICKR_SEARCH["model_key"]][FLICKR_SEARCH["geo_model_key"]]

        if geo_model is None:
            return []

        return geo_model
