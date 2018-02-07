FLICKR_SEARCH = {
    "url": "https://www.flickr.com/search/?text={0}",
    "picture_link_selector": "div.photo-list-photo-interaction a.overlay",
    "load_more_selector": ".infinite-scroll-load-more button",
    "model_export_selector": "script.modelExport",
    "model_export_pattern": "modelExport: ({.*})",
    "model_key": "main",
    "geo_model_key": "photo-geo-models"
}

SELENIUM = {
    "scroll_to_bottom_script": "window.scrollTo(0, document.body.scrollHeight);",
    "scroll_height_script": "return document.body.scrollHeight",
    "slice_array_script": "return Array.prototype.slice.call(document.querySelectorAll('{0}'), {1});"
}

FLICKR_DB = {
    "db_name": "flickr.db",
    "geo_table_name": "flickr_geo",
    "geo_create_table_sql":
        "CREATE TABLE IF NOT EXISTS {} (id bigint PRIMARY KEY, latitude decimal(9,6), longitude decimal(9,6))",
    "geo_insert_into_table_sql": "INSERT INTO {} ('id', 'latitude', 'longitude') VALUES (?, ?, ?)",
    "geo_select_all_sql": "SELECT * FROM {}"
}

FLICKR_API = {
    "host": "localhost",
    "port": "8888"
}

DB_API = {
    "host": "localhost",
    "port": "8889",
    "geo_path": "/flickr/geo/"
}
