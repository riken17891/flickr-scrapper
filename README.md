# flickr-scrapper


## Prerequisites

1. python 3.6
2. aiohttp==2.3.10
3. selenium==3.8.1
4. tornado==4.5.2
5. beautifulsoup4==4.6.0
6. chromedriver==2.35


## 1. selenium_api.py

### class: FlickrSearch
Provides methods to navigate throught the flickr search web page and pull in any picture links, It utilizes selenium module with chrome driver.

### class: FlickrImagePage
Provides methods to parse and get Model Objects from flickr image web page and provides a way to pull in image specific information, It utilizes beautifulsoup module.

## 2. flickr_api.py
Provides end point to start scrapping any place/city related images from flickr, also extracts GPS related info from scrapped images and inserts it into the Database by utilizing centralized DB Operations related API, It utilizes Tornado's Async functionality along with AsyncIO module.

### USAGE:

RUN python flickr_api.py
  
GET /start/search/{city/place} . e.g, /start/search/newyork

## 3. db_api.py
Provides methods to perform db related oprations using sqlite db, It utilizes python's OOTB sqlite3 module.

## 4. flickr_db_ops_api.py
Provides end point to insert flickr image GPS related info to Database, It utilizes Tornado's Async functionality alogn with AsyncIO module.

### USAGE:

RUN python flickr_db_ops_api.py

POST /flickr/geo (Accepts json array of geo models)

[{"_flickrModelRegistry": "photo-geo-models", "hasGeo": true, "latitude": 40.785626, "longitude": -73.9361, "accuracy": 16, "isPublic": true, "id": "24848144019"}]


GET /flickr/geo (Returns all geo models from Database)
    
