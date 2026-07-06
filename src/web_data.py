import urllib.request
import json
import re
from html.parser import HTMLParser
from fastapi import HTTPException

class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = None
        self.description = None
        self.og_title = None
        self.og_description = None
        self.og_image = None
        self.og_site_name = None
        self.og_type = None
        self.favicon = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            prop = attrs_dict.get("property", "").lower()
            content_val = attrs_dict.get("content", "")
            if name == "description":
                self.description = content_val
            elif prop == "og:title":
                self.og_title = content_val
            elif prop == "og:description":
                self.og_description = content_val
            elif prop == "og:image":
                self.og_image = content_val
            elif prop == "og:site_name":
                self.og_site_name = content_val
            elif prop == "og:type":
                self.og_type = content_val
        elif tag == "link" and attrs_dict.get("rel") in (["icon"], ["shortcut", "icon"]):
            self.favicon = attrs_dict.get("href")

    def handle_data(self, data):
        if self._in_title:
            self.title = data.strip()
            self._in_title = False

def get_url_metadata(url: str):
    """Fetch and parse metadata from a URL for unfurling/preview."""
    if not url.startswith("http"):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgentServices/1.0 Bot"})
        resp = urllib.request.urlopen(req, timeout=10)
        html = resp.read().decode("utf-8", errors="ignore")[:50000]
        parser = _MetaParser()
        parser.feed(html)
        return {
            "url": url,
            "title": parser.og_title or parser.title or "",
            "description": parser.og_description or parser.description or "",
            "image": parser.og_image,
            "site_name": parser.og_site_name,
            "type": parser.og_type,
            "favicon": parser.favicon,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))