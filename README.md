# autologin
AutoLogin is a crawling utility that attempts to automatically find the login page of a website given a seed url, and then automatically login to that website given valid credentials. AutoLogin can be used both as a library or as a service. This service gives you an easy way to handle autologin without having to find the login form yourself or build POST requests to login. You can just specify any reasonable starting point to crawl a website (e.g. the home page), give AutoLogin a set of credentials and it logs in for you, providing the authenticated headers/cookies back to you for use in your own crawler or scraper. 

Docs and usage are in docs/_build/index.html.
