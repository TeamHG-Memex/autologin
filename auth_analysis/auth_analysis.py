import requests
import pickledb
import json
from operator import itemgetter

class AuthHeaderFinder(object):

    def __init__(self, db_name = "/tmp/autologin.db"):
        self.db = pickledb.load(db_name, False)
        self.url_auth_words = ["login", "session", "auth"]

    def get_auth_items(self):
        auth_items = []
        for url in self.db.lgetall("auth_urls"):
            auth_items.append(self.db.get(url))

        return auth_items

    def match_url_auth_words(self, url):

        for url_auth_word in self.url_auth_words:
            if url_auth_word in url.lower():
                return True

        return False

    def get_scored_auth_items(self):

        scored_auth_items = []
        for auth_item in self.get_auth_items():
            
            auth_score = 0

            if "redirect_urls" in auth_item["request_meta"]:
    
                for redirect_url in auth_item["request_meta"]["redirect_urls"]:
                    if self.match_url_auth_words(redirect_url):
                        auth_score += 10
                        break

            #score based on initially requested url, matching words
            if "redirect_urls" in auth_item["request_meta"]:
                original_url = auth_item["request_meta"]["redirect_urls"][0]
            else:
                original_url = auth_item["request_url"]

            if self.match_url_auth_words(original_url):
                print "adding for original url match"
                auth_score += 10

            #score based on if there's a cookie field
            if "Cookie" in auth_item["auth_headers"]:
                print "adding for cookie"
                auth_score += 10

                #if there's a cookie field and appears to issue session token, add to score
                cookie_value = auth_item["auth_headers"]["Cookie"][0]
                #sessi is on purpose to catch common stuff like JSESSID or PHPSESSID
                if "sessi" in cookie_value.lower():
                    print "adding for sess i in cookie"
                    auth_score += 10

            #if the response was redirected add to score (but just a bit!)
            if "redirect_urls" in auth_item["response_meta"]:
                print "adding for redirect (but just a little)"
                auth_score += 5

            if "Referer" in auth_item["auth_headers"]:
                referer_url = auth_item["auth_headers"]["Referer"][0]
                if self.match_url_auth_words(referer_url):
                    print "adding for match in referer"
                    auth_score += 10
                    
                    
            auth_item["auth_score"] = auth_score
            scored_auth_items.append(auth_item)

        return sorted(scored_auth_items, key=itemgetter('auth_score'), reverse = True)

    def get_auth_header(self):
        #well ok, it's just a guess at the auth header...
        return self.get_scored_auth_items()[0]

    def send_authenticated_request(self, url, format = "requests"):

        if format == "requests":
            auth_headers_raw = self.get_auth_header()

            auth_headers_for_requests = {}
            for key, val in auth_headers_raw.iteritems():
                auth_headers_for_requests[key] = val[0]

            return requests.get(url, headers = auth_headers_for_requests)

        elif format == "scrapy":
            raise Exception("Functionality not yet implemented because I don't know how to do this")

    def test_request(self):

        auth_headers = self.get_possible_auth_headers()[0]["auth_headers"]

        print "using auth headers %s" % str(auth_headers)

        print json.dumps(auth_headers)
        print auth_headers
        auth_headers_for_requests = {}
        for key, val in auth_headers.iteritems():
            auth_headers_for_requests[key] = val[0]
  
        print auth_headers_for_requests
        r = requests.get("https://hyperiongray.atlassian.net/secure/Dashboard.jspa", headers = auth_headers_for_requests, allow_redirects = True)
        print r.text        

if __name__ == "__main__":
    ahf = AuthHeaderFinder()
#    print json.dumps(ahf.get_possible_auth_headers())
#    ahf.test_request()
    print json.dumps(ahf.get_scored_auth_items())
    for sai in ahf.get_scored_auth_items():
        print sai["auth_score"]
        
        