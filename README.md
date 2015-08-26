# Autologin: Automatic login for web spiders
AutoLogin is a utility that makes it easier for web spiders to **crawl websites that require login**. Provide it with credentials and a URL or the html source of a page(normally the homepage), and it will attempt to login for you. Cookies are returned to be used by your spider.

The goal of Autologin is to make it easier for web spiders to crawl websites that require authentication **without having to re-write login code for each website.**

Autologin can be used as a library, on the command line, or as a service. You can make use of Autologin without generating http requests, so you can drop it right into your spider without worrying about the impacting rate limits.

Autologin is written in Python and only requires lxml and Flask in order to do its thing. However if you install Formasaurus (and you should) it will use it automatically and performance will improve.

## Code Example

Show what the library does as concisely as possible, developers should be able to figure out **how** your project solves their problem by looking at the code example. Make sure the API you are showing off is obvious, and that your code is short and concise.

## Installation
This is not (yet) registered on PyPi so you clone the repository and then use setup.py:
```
$ git clone 
```


## API Reference

Depending on the size of the project, if it is small and simple enough the reference docs can be added to the README. For medium size to larger projects it is important to at least provide a link to where the API reference docs live.

## Tests

Describe and show how to run the tests with code examples.

## Contributors

Let people know how they can dive into the project, include important links to things like issue trackers, irc, twitter accounts if applicable.

## License

A short snippet describing the license (MIT, Apache, etc.)
