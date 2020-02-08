from urllib.parse import urlencode
import pymongo
import requests
from lxml.etree import XMLSyntaxError
from requests.exceptions import ConnectionError
from pyquery import PyQuery as pq
from config import *

client = pymongo.MongoClient(MONGO_URI)
db = client[MONGO_DB]

base_url = 'http://weixin.sogou.com/weixin?'

headers = {
    'Cookie': 'SUV=00AF98DC7A73EB125D8A2E8B89C7C932; SUID=B5C2036A3D148B0A5DFC4FA0000A2A1A; wuid=AAGa+zTYKwAAAAqLFD3gDwgApwM=; CXID=CF008E7D7E219FDBF8CD85C93E4C3766; ad=6ujHyZllll2Wn7PAlllllVcfhpklllllzk5jHyllllwlllllxv7ll5@@@@@@@@@@; ABTEST=4|1581150195|v1; SNUID=6C1BDAB3D9DC47D6EE669C20DA2A01E3; IPLOC=CN1100; weixinIndexVisited=1; JSESSIONID=aaaGfJhvFRj9XeX2kgq_w; ppinf=5|1581152346|1582361946|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToyNzolRTYlOUMlOUQlRTYlOUMlOUQlRTYlOUMlOUR8Y3J0OjEwOjE1ODExNTIzNDZ8cmVmbmljazoyNzolRTYlOUMlOUQlRTYlOUMlOUQlRTYlOUMlOUR8dXNlcmlkOjQ0Om85dDJsdUZLM1NzMFU3WDJSVW9OTGs2bldCUUVAd2VpeGluLnNvaHUuY29tfA; pprdig=VAESNdeGfn3O9VyV3855mbJ9PK-UsoXpP9Sxkgv121DF1IGAYcdrAOBEweIig-UowKgA0DUoGVWX-4b4ddybONQR6ZsZeKTkKQBvioSKUomhvPVBK0ZoTMdEGv77NcmaGZDNLrI-1tdc7aq3oIx30VMBQ40BdyKPrs0wBHC628s; sgid=28-45712927-AV4ibeFpUl8PGdKHfZzwFWxU; ppmdig=15811523460000000c7c2f0419dccfc680087e378e76f1eb',
    'Host': 'weixin.sogou.com',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36'
}

proxy = None


def get_proxy():
    try:
        response = requests.get(PROXY_POOL_URL)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def get_html(url, count=1):
    print('Crawling', url)
    print('Trying Count', count)
    global proxy
    if count >= MAX_COUNT:
        print('Tried Too Many Counts')
        return None
    try:
        if proxy:
            proxies = {
                'http': 'http://' + proxy
            }
            response = requests.get(url, allow_redirects=False, headers=headers, proxies=proxies)
        else:
            response = requests.get(url, allow_redirects=False, headers=headers)
        if response.status_code == 200:
            return response.text
        if response.status_code == 302:
            # Need Proxy
            print('302')
            proxy = get_proxy()
            if proxy:
                print('Using Proxy', proxy)
                return get_html(url)
            else:
                print('Get Proxy Failed')
                return None
    except ConnectionError as e:
        print('Error Occurred', e.args)
        proxy = get_proxy()
        count += 1
        return get_html(url, count)



def get_index(keyword, page):
    data = {
        'query': keyword,
        'type': 2,
        'page': page
    }
    queries = urlencode(data)
    url = base_url + queries
    html = get_html(url)
    return html

def parse_index(html):
    doc = pq(html)
    items = doc('.news-box .news-list li .txt-box h3 a').items()
    for item in items:
        yield item.attr('href')

def get_detail(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.text
        return None
    except ConnectionError:
        return None

def parse_detail(html):
    try:
        doc = pq(html)
        title = doc('.rich_media_title').text()
        content = doc('.rich_media_content').text()
        date = doc('#post-date').text()
        nickname = doc('#js_profile_qrcode > div > strong').text()
        wechat = doc('#js_profile_qrcode > div > p:nth-child(3) > span').text()
        return {
            'title': title,
            'content': content,
            'date': date,
            'nickname': nickname,
            'wechat': wechat
        }
    except XMLSyntaxError:
        return None

def save_to_mongo(data):
    if db['articles'].update({'title': data['title']}, {'$set': data}, True):
        print('Saved to Mongo', data['title'])
    else:
        print('Saved to Mongo Failed', data['title'])


def main():
    for page in range(1, 11):
        html = get_index(KEYWORD, page)
        if html:
            article_urls = parse_index(html)
            for article_url in article_urls:
                article_html = get_detail(article_url)
                if article_html:
                    article_data = parse_detail(article_html)
                    print(article_data)
                    if article_data:
                        save_to_mongo(article_data)



if __name__ == '__main__':
    main()
