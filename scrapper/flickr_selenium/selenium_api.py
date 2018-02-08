import re
import json
import logging

import html5lib

import asyncio

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException

from bs4 import BeautifulSoup

from config import FLICKR_SEARCH
from config import FLICKR_API
from config import SELENIUM

logging.basicConfig(level=logging.INFO, filename=FLICKR_API["log"])
logger = logging.getLogger(__name__)


class FlickrSearch:

    def __init__(self, place):

        # add headless option to ChromeOptions
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        options.add_argument("--no-sandbox")

        self.place = place

        # initialize browser
        self.browser = webdriver.Chrome(chrome_options=options)

        # search for place and open that page
        self.open(FLICKR_SEARCH["url"].format(place))

    def open(self, url):
        self.browser.get(url)

    def get_title(self):
        return self.browser.title

    @asyncio.coroutine
    def get_all_images(self, queue):
        last_end = 0
        # scroll to bottom on initial load
        self.scroll_to_bottom()

        while True:
            # get all image links starting from last_end value, defaults to 0
            links = self.get_all_image_links(start=last_end)

            # loop through all image links and add to queue
            for element in links:
                href = element.get_attribute("href")

                logging.info("Adding : {} : {}".format(self.place, href))

                yield from queue.put(href)

            # if number of retrieved links are 0 then break the loop
            if len(links) == 0:
                break

            # change number of retrieved links to last_end to start getting links from that number only
            last_end += len(links)
            logging.info("Links Retrieved : {} : {}".format(self.place, str(last_end)))

            """
            run loop 5 times and either look for "load_more" button to click or scroll to bottom to load more images in 
            view. wait for 5 seconds after each time to give 5 seconds to load images in a view. 
            Using async sleep to not to block other io processing
            """
            for _ in range(5):
                if self.check_and_click_if_load_more_exists() or self.scroll_to_bottom():
                    yield from asyncio.sleep(5)

    def scroll_to_bottom(self):
        # scroll to bottom
        self.browser.execute_script(SELENIUM["scroll_to_bottom_script"])
        return True

    def scroll_height(self):
        # get new height of view
        return self.browser.execute_script(SELENIUM["scroll_height_script"])

    def check_and_click_if_load_more_exists(self):
        try:
            # check if load_more button exists and if yes, then click
            load_more_button = self.browser.find_element_by_css_selector(FLICKR_SEARCH["load_more_selector"])
            self.browser.execute_script("arguments[0].click();", load_more_button)
            return True
        except NoSuchElementException:
            return False

    def get_all_image_links(self, start=0):
        # get all links by selector and start index for list
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
        # retrieve script tag and get text from it
        script_tag = soup.select_one(FLICKR_SEARCH["model_export_selector"])

        if script_tag is None:
            return {}

        script_content = script_tag.get_text()

        # match model variable pattern and get json string from it
        pattern = re.compile(FLICKR_SEARCH["model_export_pattern"])
        json_string = pattern.search(script_content).group(1)

        # return pulled json as dict
        return json.loads(json_string)

    def get_geo_model(self):
        if not self.model:
            return []

        # pull geo model from dict
        geo_model = self.model[FLICKR_SEARCH["model_key"]][FLICKR_SEARCH["geo_model_key"]]

        if geo_model is None:
            return []

        # return pulled geo model as dict
        return geo_model
