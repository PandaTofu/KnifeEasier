#!/usr/bin/env python
# -*- coding: utf-8 -*-

import base64
import json
import time, datetime
import http.client, urllib
from html.parser import HTMLParser



ACCEPT = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
ACCEPT_ENCODING = "gzip, deflate, sdch, br"
ACCEPT_LAN = "en-US,en;q=0.8"
CACHE_CONTROL = "max-age=0"
CONNECTION = "keep-alive"
CONTENT_TYPE = "application/x-www-form-urlencoded"
USER_AGENT = "Mozilla/5.0 (Windows NT 6.1; Win64; x64) " \
             "/AppleWebKit/537.36 (KHTML, like Gecko) " \
             "Chrome/58.0.3029.110 Safari/537.36"


class ReqError(Exception):
    def __init__(self, errorcode, msg):
        self.err = errorcode
        self.msg = msg


class TokenHTMLParser(HTMLParser):
    def __init__(self):
        super(TokenHTMLParser, self).__init__()
        self.set_flag = False
        self.crsf_token = None

    def handle_starttag(self, tag, attrs):
        if self.crsf_token is not None:
            return
        if tag == "meta":
            meta_dict = dict()
            for name, value in attrs:
                meta_dict[name] = value
            if meta_dict.get("name", None) == "csrf-token":
                self.csrf_token = meta_dict.get("content", None)

    def get_csrf_token(self):
        return self.csrf_token

    def pahse(self, html):
        try:
            self.feed(html)
        except Execption as e:
            raise ReqError(300, "Fail to phase html, exception:%s" % e.msg)


class RefHTMLParser(HTMLParser):
    def __init__(self):
        super(RefHTMLParser, self).__init__()
        self.set_flag = False
        self.refID_dict = dict()
        self.isHandleData = False
        self.current_refID = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for name, value in attrs:
                if name == "onclick":
                    self.parse_refID(value)

    def parse_refID(self, content):
        items = content.split("$")
        for item in items:
            if "#knife_request_reference_id" in item:
                attrs = item.split(".")
                for attr in attrs:
                    if attr.startswith("val"):
                        self.current_refID = attr.split("\'")[1]


    def handle_data(self, data):
        if self.current_refID:
            self.refID_dict[data.strip()] = self.current_refID

    def handle_endtag(self, tag):
        if tag == "a":
            self.current_refID = None

    def handle_charref(self, name):
        print("Name:%s" % name)

    def get_refID_dict(self):
        return self.refID_dict

    def pahse(self, html):
        try:
            self.feed(html)
        except Execption as e:
            raise ReqError(300, "Fail to phase html, exception:%s" % e.msg)


class WftHttpsClient():
    def __init__(self, user, passwd):
        self.user = user
        self.passwd = passwd
        self.wam_host = "wam.inside.nsn.com"
        self.wft_host = "wft.int.net.nokia.com"
        self.wam_headers = {
            "Accept": ACCEPT,
            "Accept-Encoding": ACCEPT_ENCODING,
            "Accept-Language": ACCEPT_LAN,
            "Cache-Control": CACHE_CONTROL,
            "Connection": CONNECTION,
            "Content-Type": CONTENT_TYPE,
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": USER_AGENT
        }
        self.wft_headers = {
            "Accept": ACCEPT,
            "Accept-Language": ACCEPT_LAN,
            "Cache-Control": CACHE_CONTROL,
            "Connection": CONNECTION,
            "Content-Type": CONTENT_TYPE,
            "Cookie": None,
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": USER_AGENT
        }

        # get SMSESSION and token
        self.sm_session = self.get_smsession()
        self.crsf_token = self.get_crsf_token(self.sm_session)


    def set_cookie(self, cookie):
        self.wft_headers["Cookie"] = cookie

    def request(self, host, isHttps=True, method="GET", path="/", params=None, headers=None):
        if isHttps:
            host_connect = http.client.HTTPSConnection(host)
        else:
            host_connect = http.client.HTTPConnection(host)

        if not headers:
            if host == self.wam_host:
                headers = self.wam_headers
            elif host == self.wft_host:
                headers = self.wft_headers

        if params:
            body = urllib.parse.urlencode(params)
            with open("params.txt", 'w') as fp:
                fp.write(body)
        else:
            body = None


        host_connect.request(method, path, body=body, headers=headers)
        return host_connect.getresponse()

    def post(self, host, isHttps=True, path="/", params=None, headers=None):
        return self.request(host, isHttps=isHttps, method="POST", path=path, params=params, headers=headers)

    def get(self, host, isHttps=True, path="/", headers=None):
        return self.request(host, isHttps=isHttps, method="GET", path=path, headers=headers)

    def get_smsession(self):
        auth_params = {"SMENC": "ISO-8859-1", "SMLOCALE": "US-EN",
                       "USER": self.user, "PASSWORD": self.passwd,
                       "target": "https://wam.inside.nsn.com/", "smauthreason": "0"}
        login_path = "/siteminderagent/forms/login.fcc"
        response = self.post(self.wam_host, path=login_path, params=auth_params)
        cookie = response.getheader("set-cookie")
        sm_session = None
        if "SMSESSION" in cookie:
            temp_str = cookie.split("SMSESSION")[1]
            temp_str = temp_str.split(";", 1)[0]
            sm_session = "SMSESSION%s" % temp_str
        if sm_session is None:
            raise ReqError(301, "SMSESSION failure.")

        return sm_session

    def get_crsf_token(self, sm_session):
        self.set_cookie(sm_session)
        new_knife_path = "/ALL/knife_requests/new"
        response = self.get(self.wft_host, path=new_knife_path)

        html_data = response.read().decode()
        html_parser = TokenHTMLParser()
        html_parser.pahse(html_data)
        crsf_token = html_parser.get_csrf_token()
        if crsf_token is None:
            raise ReqError(302, "crsf_token failure.")

        return crsf_token

    def query_baseline(self, baselineID):
        query_headers = {"Accept": "application/json, text/javascript, */*; q=0.01",
                         "Accept-Language": ACCEPT_LAN,
                         "Connection": CONNECTION,
                         "Cookie": self.sm_session,
                         "User-Agent": USER_AGENT,
                         "X-CSRF-Token": self.crsf_token,
                         "X-Requested-With": "XMLHttpRequest"}
        query_path = "/knife_requests/autocomplete?source=baseline&term=%s&_type=query" % baselineID
        response = self.get(self.wft_host, path=query_path, headers=query_headers)
        if response.status != 200:
            raise ReqError(303, "Query baseline failure, status:%s" % response.status)
        return json.loads(response.read().decode())

    def query_reference(self, refID):
        query_headers = {"Accept": "*/*",
                         "Accept-Language": ACCEPT_LAN,
                         "Connection": CONNECTION,
                         "Cookie": self.sm_session,
                         "User-Agent": USER_AGENT,
                         "X-CSRF-Token": self.crsf_token,
                         "X-Requested-With": "XMLHttpRequest"}
        query_params = {"element": "knife_request_reference_id",
                        "type": "Fault,Feature",
                        "q": refID,
                        "utf8": "✓",
                        "authenticity_token": self.crsf_token,
                        "items[builds]": 1,
                        "items[faults]": 1,
                        "items[features]": 1,
                        "items[build_attachments]": 1,
                        "search": ""}
        query_path = "/common/select_live?%s" % urllib.parse.urlencode(query_params)
        response = self.get(self.wft_host, path=query_path, headers=query_headers)
        if response.status != 200:
            raise ReqError(304, "Query reference failure, status:%s" % response.status)

        html_data = response.read().decode()
        html_parser = RefHTMLParser()
        html_parser.pahse(html_data)
        return html_parser.get_refID_dict()

    def create_knife(self, knife_conf):
        knife_conf.append(("authenticity_token", self.crsf_token))
        knife_request_path = "/ALL/knife_requests"
        response = self.post(self.wft_host, path=knife_request_path, params=knife_conf)
        print(response.status)
        created_url = response.getheader("Location")
        if created_url is None:
            raise ReqError(305, "Knife request failure.")

        return created_url
