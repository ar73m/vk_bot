# -*- coding: utf-8 -*-
# This is a template for a Python scraper on morph.io (https://morph.io)
# including some code snippets below that you should find helpful

# import scraperwiki
# import lxml.html
#
# # Read in a page
# html = scraperwiki.scrape("http://foo.com")
#
# # Find something on the page using css selectors
# root = lxml.html.fromstring(html)
# root.cssselect("div[align='left']")
#
# # Write out to the sqlite database using scraperwiki library
# scraperwiki.sqlite.save(unique_keys=['name'], data={"name": "susan", "occupation": "software developer"})
#
# # An arbitrary query against the database
# scraperwiki.sql.select("* from data where 'name'='peter'")

# You don't have to do things with the ScraperWiki and lxml libraries.
# You can use whatever libraries you want: https://morph.io/documentation/python
# All that matters is that your final data is written to an SQLite database
# called "data.sqlite" in the current working directory which has at least a table
# called "data".
# https://github.com/scraperwiki/scraperwiki-python
# http://effbot.org/zone/element-xpath.htm

import scraperwiki
import lxml.html
import os
import time
import urlparse
import json

from datetime import datetime
from grab import Grab


def my_logger(url, status, headers, message):
    if DEBUG:
        print("Message: {0}".format(message))
        print("URL: {0}".format(url))
        print("Status: {0}".format(status))
        print("Headers:")
        for i in headers.keys():
            print("{0}: {1}".format(i, headers[i]))

            
def my_print_data(user_data):
    if DEBUG:
        for key in user_data.keys():
            print("{0}: {1}".format(key, user_data[key][0]))
        
        
DEBUG = False

USER_AGENT = os.environ['MORPH_USER_AGENT']
USERNAME = os.environ['MORPH_USERNAME']
PASSWORD = os.environ['MORPH_PASSWORD']
VK_APP_ID = os.environ['MORPH_VK_APP_ID']

VK_AUTH_URL = "https://oauth.vk.com/authorize?" \
              "client_id={0}&display={1}&redirect_uri={2}&" \
              "scope={3}&response_type={4}&v=5.35".format(
                    VK_APP_ID, "mobile", "https://oauth.vk.com/blank.html",
                    "friends", "token"
            )
VK_API_URL = "https://api.vk.com/method/{method}?{params}&v=5.35&access_token={access_token}"
            
def query_vk(g, method, params, access_token):
    # Example https://api.vk.com/method/users.get?access_token=d6506a3
    # https://vk.com/dev/methods
    url = VK_API_URL.format(method=method, params=params, access_token=access_token)
    resp = g.go(url)
    return resp.body
    
    
            
def auth_vk(g):
    # Define data to send
    login_data = {
                    'to': '',
                    '_origin': '',
                    'ip_h': '',
                    'lg_h': '',
                    'email': USERNAME, 
                    'pass': PASSWORD
                }

    # First Step
    resp = g.go(url=VK_AUTH_URL)
    my_logger(resp.url, resp.status, resp.headers, "Welcome page")
    html_str = resp.body
    vk_wellcome = lxml.html.fromstring(html_str)
    
    # Fill login data
    login_data['to'] = vk_wellcome.xpath('//input[@name="to"]/@value')[0]
    login_data['_origin'] = vk_wellcome.xpath('//input[@name="_origin"]/@value')[0]
    login_data['ip_h'] = vk_wellcome.xpath('//input[@name="ip_h"]/@value')[0]
    login_data['lg_h'] = vk_wellcome.xpath('//input[@name="lg_h"]/@value')[0]

    time.sleep(4)
    # Second Step (Send login data)
    resp = g.go(url="https://login.vk.com/?act=login&soft=1&utf8=1", post=login_data)
    my_logger(resp.url, resp.status, resp.headers, "")

    # Third Step (302 Redirect)
    resp = g.go(resp.headers['Location'])
    my_logger(resp.url, resp.status, resp.headers, "Redirect 302 1")

    # Fourth Step (302 Redirect)
    resp = g.go(resp.headers['Location'])
    my_logger(resp.url, resp.status, resp.headers, "Redirect 302 2")

    loc = resp.headers['Location']
    user_data = urlparse.parse_qs(loc.split('#')[1])
    my_print_data(user_data)
    # return keys access_token, expires_in, user_id
    return {'user_id': user_data['user_id'][0], 
            'expires_in': user_data['expires_in'][0],
            'access_token': user_data['access_token'][0]}

def start_scrape():
    # Init and setting Grab
    g = Grab(timeout=10, user_agent=USER_AGENT)
    g.setup(proxy='91.204.112.48:8080', proxy_type='https', connect_timeout=25, timeout=25, follow_location=False, follow_refresh=False)
    
    user = auth_vk(g)
    
    data = {'method': 'friends.getOnline',
            'params': '',#'online_mobile=1',
            'access_token': user['access_token']}
    
    response = json.loads(query_vk(g, **data))["response"]

    if len(response) > 0:
        data = {'method': 'users.get',
            'params': 'user_ids={0}&fields=domain'.format(",".join(str(id) for id in response)),
            'access_token': user['access_token']}
            
        
        response = json.loads(query_vk(g, **data), "utf-8")["response"]
        
        if len(response) > 0:
            for i in response:
                print(u"{0} - {1} - {2}".format(u"http://vk.com/{}".format(i["domain"]), 
                        u"{0} {1}".format(i["first_name"], i["last_name"]),   
                        datetime.strftime(datetime.now(), '%Y/%m/%d %H:%M:%S')).encode('cp866', errors='replace'))
                scraperwiki.sqlite.save(unique_keys=['id'], 
                data={  'id': i["id"],
                        'url': u"http://vk.com/{}".format(i["domain"]), 
                        'name': u"{0} {1}".format(i["first_name"], i["last_name"]),
                        'update_date': datetime.strftime(datetime.now(), u'%Y/%m/%d %H:%M:%S')})
            print("Count: {}".format(len(response)))

if __name__ == '__main__':
    start_scrape()