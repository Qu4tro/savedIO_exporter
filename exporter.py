import cookielib
import itertools
import logging
import json
import time
import sys
from getpass import getpass

from BeautifulSoup import BeautifulSoup
import mechanize

import coloredlogs

import click

#Thanks to these threads:
# http://stackoverflow.com/questions/20039643/how-to-scrape-a-website-that-requires-login-first-with-python
# http:/stackoverflow.com/questions/21190395/python-mechanize-login

logger = logging.getLogger(__name__)
coloredlogs.install(level=logging.INFO)

def setup_browser():

    logger.info("Setting up browser")
    # Browser
    browser = mechanize.Browser()

    # Cookie Jar
    cj = cookielib.LWPCookieJar()
    browser.set_cookiejar(cj)

    # Browser options
    browser.set_handle_equiv(True)
    browser.set_handle_redirect(True)
    browser.set_handle_referer(True)
    browser.set_handle_robots(False)
    browser.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)

    browser.addheaders = [('User-agent', 'Chrome')]

    return browser


def login(browser, email, password):

    logger.info("Logging in saved.io")
    browser.select_form(nr=0)

    # User credentials
    browser.form['myemail'] = email
    browser.form['mypassword'] = password

    # Login
    browser.submit()

    if is_logged_in(browser):
        logger.info("Logging successful")
    else:
        logger.info("Logging not successful")
        print("Login not successful. Exiting...")
        sys.exit(1)

def is_logged_in(browser):
    soup = get_soup(browser)
    header = soup.find('h2').string

    logger.debug("Header: {0}".format(soup.find('h2')))
    logger.debug("Header after login: {0}".format(header))

    if header == u'Your Bookmarks':
        return True
    else:
        return False


def get_soup(browser, listkey=0, page=1):

    generic_url = "http://saved.io/?page={0}.&listl={1}"
    url = generic_url.format(page, listkey)

    logger.debug("Getting soup from: {0}".format(url))
    logger.debug("Sleeping a few seconds to let the server rest :-)")
    time.sleep(3)

    return BeautifulSoup(browser.open(url).read())

def get_lists(browser):

    logger.info("Getting all your lists")
    lists = {}

    soup = get_soup(browser)
    customDropdown = soup.find("select", { "id" : "customDropdown" })
    options = customDropdown.findAll("option")

    for option in options:
        lists[option.get('value')] = option.string
        logger.debug(option.string)
    
    del lists[u'0']

    return lists


def scrape_list(browser, listkey):

    bookmarks = []

    for page in itertools.count(1):

        logger.debug("Page {0}".format(page))

        soup = get_soup(browser, listkey, page)
        divs = soup.findAll("div", { "class" : "bookmark" })

        logger.debug("Number of bookmarks: {0}".format(len(divs)))
        if divs:
            for html in divs:
                link = html.find('a', {"class": "linkage"}).get('href')
                bookmarks.append(link)
        else:
            break

    return bookmarks


def scrape(browser):

    bookmarks = {}
    
    lists = get_lists(browser)

    for (i, listkey) in enumerate(lists):

        logger.info("Scraping {0} ({1}/{2})".format(lists[listkey], i, len(lists)))
    
        links = scrape_list(browser, listkey)
        bookmarks[lists[listkey]] = links

    return bookmarks

def output(bookmarks, out=None):

    logger.info("Generating output.")
    
    dumped = json.dumps(bookmarks, indent=4, sort_keys=True)

    if out == None:
        sys.stdout.write(dumped)
    else:
        with open(out, 'w') as f:
            f.write(dumped)

@click.command()
@click.option('--email', '-e', default=None, help="User's email. If you choose to omit this option, you will be prompt on the terminal to complete this field.")
@click.option('--password', '-p', default=None, help="User's password. If you choose to omit this option, you will be prompt on the terminal to complete this field.")
@click.option('--outfile', '-o', default=None, help="Place output in file specified.")
@click.option('--verbose', '-v', count=True, help="Increase verbosity levels from none to -vv")
def main(email=None, password=None, outfile=None, verbose=0):

    "This script downloads your saved.io bookmarks into a nice json file."
    
    if email is None:
        email = raw_input("Please, provide your email: ")
    if password is None:
        password = getpass("Please, provide your password: ")

    if verbose == 0:
        logger.disabled = True
    if verbose == 1:
        coloredlogs.set_level(logging.INFO)
    if verbose >= 2:
        coloredlogs.set_level(logging.DEBUG)

    browser = setup_browser()
    browser.open("http://saved.io")
    login(browser, email, password)

    bookmarks = scrape(browser)
    output(bookmarks, outfile)

    logger.info("Done.")

if __name__ == '__main__':
    main()

