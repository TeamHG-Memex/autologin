# Autologin: Automatic login for web spiders
AutoLogin is a utility that makes it easier for web spiders to **crawl websites that require login**. Provide it with credentials and a URL or the html source of a page(normally the homepage), and it will attempt to login for you. Cookies are returned to be used by your spider.

The goal of Autologin is to make it easier for web spiders to crawl websites that require authentication **without having to re-write login code for each website.**

Autologin can be used as a library, on the command line, or as a service. You can make use of Autologin without generating http requests, so you can drop it right into your spider without worrying about impacting rate limits.

Autologin is written in Python and only requires lxml and Flask in order to do its thing. However if you install Formasaurus (and you should) it will use it automatically and performance will improve.

## Quickstart
Don't like reading documentation? 
```python
from autologin.autologin import AutoLogin

url = 'https://reddit.com'
username = 'foo'
password = 'bar'
al = AutoLogin()
cookies = al.auth_cookies_from_url(url, username, login)
```
You now have a [cookiejar](https://docs.python.org/2/library/cookielib.html) that you can use in your spider.
Don't want a cookiejar? 
```python
cookies.__dict__
```
You now have a dictionary.

## Features
* Automatically find login forms and fields
* Obtain authenticated cookies
* Obtain form requests to submit from your own spider
* Extract links to login pages
* Use as a library with or without making http requests
* Command line client
* Web service for testing your requests and cookies


[Installation](##Installation)
[Auth Cookies From URL](##Auth cookies from URL)
[Auth Cookies From HTML](##Auth cokies from HTML)
[Login request](##Login request)
[Extract login links](##Extract login links)
[Command Line](##Command Line)
[Web Service](##Web Service)

## Installation
This is not (yet) registered on PyPi so you must clone the repository and use setup.py to build and install:
```
$ git clone https://github.com/TeamHG-Memex/autologin.git
$ cd autologin
$ python setup.py build
$ python setup.py install
```

## Auth cookies from URL
This method makes an http request to the URL using urllib, extracts the login form (if there is one), fills the fields and submits the form. It then return any cookies it has picked up.
```
cookies = al.auth_cookies_from_url(url, username_password)
```
Note that it returns all cookies, they may be session cookies rather than authenticated cookies.


## Auth cookies from HTML

## Login request

## Extract login links

## Command Line
```
$ autologin
usage: autologin [-h] [--proxy PROXY] [--show-in-browser SHOW_IN_BROWSER]
                 username password url
```

## Web Service
```
$ autologin-server
 * Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)
 * Restarting with stat
```


## Tests

Describe and show how to run the tests with code examples.

## Contributors

Let people know how they can dive into the project, include important links to things like issue trackers, irc, twitter accounts if applicable.

## License

A short snippet describing the license (MIT, Apache, etc.)
