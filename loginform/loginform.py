#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from collections import defaultdict
from lxml import html

__version__ = '1.0'  # also update setup.py

class LoginFormFinder(object):

    def __init__(self, url, body, username, password):

        self.username =  username
        self.password= password
        doc = html.document_fromstring(body, base_url=url)
        self.top_form, self.top_form_score = self.get_top_form(doc.xpath('//form'))

    def form_score(self, form):
        score = 0
        # In case of user/pass or user/pass/remember-me
        if len(form.inputs.keys()) in (2, 3):
            score += 10
    
        typecount = defaultdict(int)
        for x in form.inputs:
            type_ = x.type if isinstance(x, html.InputElement) else "other"
            typecount[type_] += 1
    
        if typecount['text'] > 1:
            score += 10
        if not typecount['text']:
            score -= 10
    
        if typecount['password'] == 1:
            score += 10
        if not typecount['password']:
            score -= 10
    
        if typecount['checkbox'] > 1:
            score -= 10
        if typecount['radio']:
            score -= 10
    
        return score
    
    def get_top_form(self, forms):
        """Return the form most likely to be a login form"""
        all_forms = sorted(forms, key=self.form_score, reverse=True)
        top_form = all_forms[0]
        return top_form, self.form_score(top_form)
    
    def pick_fields(self, form):
        """Return the most likely field names for username and password"""
        userfield = passfield = emailfield = None
        for x in form.inputs:
            if not isinstance(x, html.InputElement):
                continue
    
            type_ = x.type
            if type_ == 'password' and passfield is None:
                passfield = x.name
            elif type_ == 'text' and userfield is None:
                userfield = x.name
            elif type_ == 'email' and emailfield is None:
                emailfield = x.name

        return userfield or emailfield, passfield

    def submit_value(self, form):
        """Returns the value for the submit input, if any"""
        for x in form.inputs:
            if x.type == "submit" and x.name:
                return [(x.name, x.value)]
        else:
            return []

    def fill_top_login_form(self):

        userfield, passfield = self.pick_fields(self.top_form)
        self.top_form.fields[userfield] = self.username
        self.top_form.fields[passfield] = self.password
        self.top_form_values = self.top_form.form_values() + self.submit_value(self.top_form)

        return self.top_form_values, self.top_form.action or self.top_form.base_url, self.top_form.method

if __name__ == '__main__':
    def main():
        ap = ArgumentParser()
        ap.add_argument('-u', '--username', default='username')
        ap.add_argument('-p', '--password', default='secret')
        ap.add_argument('url')
        args = ap.parse_args()
    
        try:
            import requests
        except ImportError:
            print('requests library is required to use loginform as a tool')
    
        r = requests.get(args.url)
        lf = LoginFormFinder(args.url, r.text, args.username, args.password)
        
        values, action, method = lf.fill_top_login_form()
    
        #this will fail if there's unicode in any of these fields (e.g. github)
        print('url: {0}\nmethod: {1}\npayload:'.format(action, method))
        for k, v in values:
            print('- {0}: {1}'.format(k, v))
    
    main()
