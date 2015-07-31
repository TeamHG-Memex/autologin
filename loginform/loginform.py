#!/usr/bin/env python
import sys
from argparse import ArgumentParser
from collections import defaultdict
from lxml import html
from formasaurus import FormExtractor

__version__ = '1.0'  # also update setup.py

class LoginFormFinder(object):

    def __init__(self, url, body, username, password, use_formasaurus=True):

        self.username =  username
        self.password= password
        self.form_extractor = FormExtractor.load()
        doc = html.document_fromstring(body, base_url=url)
        #self.top_form, self.top_form_score = self.get_top_form(doc.xpath('//form'))
        if use_formasaurus is True or use_formasaurus == 'True':
            print 'Using Formasaurus'
            self.login_form = self.get_login_form_with_formasaurus(doc)
        else:
            print 'Using naive scoring algo'
            self.login_form, self.top_form_score =  self.get_top_form(doc.xpath('//form'))


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
        self.all_forms = sorted(forms, key=self.form_score, reverse=True)
        try:
            top_form = self.all_forms[0]
        except:
            raise Exception("No suitable form was found on the page")

        return top_form, self.form_score(top_form)
    
    def get_login_form_with_formasaurus(self, doc):
        """Return the form most likely to be a login form"""
        #self.all_forms = sorted(forms, key=self.form_score, reverse=True)
        self.all_forms = self.form_extractor.extract_forms(doc) 
        login_forms = [v[0] for i, v in enumerate(self.all_forms) if v[1] == 'l']
        try:
            login_form = login_forms[0]
        except:
            raise Exception("No suitable form was found on the page")

        return login_form

    
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

        userfield, passfield = self.pick_fields(self.login_form)

        if userfield is None:
            raise Exception("No fields found that look like userfield")

        
        if passfield is None:
            raise Exception("No fields found that look like passfield")

        self.login_form.fields[userfield] = self.username
        self.login_form.fields[passfield] = self.password
        self.login_form_values = self.login_form.form_values() + self.submit_value(self.login_form)

        return self.login_form_values, self.login_form.action or self.login_form.base_url, self.login_form.method

if __name__ == '__main__':
    
    """
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
    """
    import requests
    url = "https://github.com/login"
    r=requests.get(url)
    lff = LoginFormFinder(url, r.text, "ddd", "pass")
    print lff.fill_top_login_form()
    
    
