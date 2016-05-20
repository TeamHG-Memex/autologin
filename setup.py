import os
from setuptools import setup


# Utility function to read the README file
# Easier than line wrapping a long string...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name = "autologin",
    version = "0.1.2",
    author = "Alejandro Caceres, Luke Maxwell",
    author_email = "lukemaxwellshouse@gmail.com",
    description = ("A utility for finding login links, forms and autologging "
                   "into websites with a set of valid credentials."),
    license = "MIT",
    keywords = "login, automated, spider",
    url = "https://github.com/TeamHG-Memex/autologin",
    packages=['autologin'],
    include_package_data = True,
    install_requires = [
        'six',
        'lxml',
        'Flask==0.10.1',
        'Flask-Admin==1.4.0',
        'Flask-SQLAlchemy==2.1',
        'Flask-WTF==0.12',
        'WTForms==2.1',
        'scrapy>=1.1.0',
        'numpy',  # These 3 are formasaurus deps, make sure we always have them
        'scipy',
        'scikit-learn',
        'formasaurus[with_deps]==0.7.2',
        'scrapy-splash>=0.4',
        'crochet',
        'requests',
    ],
    entry_points = {
        'console_scripts': [
            'autologin = autologin.autologin:main',
            'autologin-server = autologin.server:main',
            'autologin-http-api = autologin.http_api:main',
        ]
    },
    long_description=read('README.rst'),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Internet :: WWW/HTTP :: Indexing/Search',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
)
