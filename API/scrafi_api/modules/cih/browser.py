# -*- coding: utf-8 -*-

# Copyright(C) 2021      Zhor Abid
#
# This file is part of a woob module.
#
# This woob module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This woob module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this woob module. If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import sys

from woob.browser import URL, need_login
from woob.browser.selenium import SeleniumBrowser, webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from .scrafi_exceptions import IdNotFoundError, WebsiteError, WrongCredentialsError, NoHistoryError

from .pages import LoginPage, HomePage, AccountsPage, HistoryPage


class CIHBrowser(SeleniumBrowser):
    BASEURL = 'https://entreprises.cihonline.ma'

    if 'linux' in sys.platform:
        from xvfbwrapper import Xvfb
        vdisplay = Xvfb(width=2920, height=1080)
        vdisplay.start()

    HEADLESS = False

    DEFAULT_WAIT = 30

    DRIVER = webdriver.Chrome(r"C:\Users\ayoub\Downloads\chromedriver_win32\chromedriver.exe")

    login_page = URL(r'/adriaClient/login/auth', LoginPage)
    home_page = URL(r'/adriaClient/app', HomePage)
    accounts_page = URL(r'/adriaClient/app/account/list', AccountsPage)
    history_page = URL(r'/adriaClient/app/account/statement', HistoryPage)

    error_msg = ''

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        super(CIHBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.login_page.go()
        try:
            self.wait_until_is_here(self.login_page)
            self.page.login(self.username, self.password)
            try:
                self.wait_until_is_here(self.home_page)
                try:
                    self.driver.find_element(By.XPATH, '//div[text()="Chargement en cours ..."]').text
                    self.wait_xpath_invisible('//div[text()="Chargement en cours ..."]')
                except NoSuchElementException:
                    pass
                self.logged = True
            except TimeoutException:
                self.error_msg = 'credentials'
                raise WrongCredentialsError
        except TimeoutException:
            print('not logged')
            self.error_msg = 'bank'
            raise WebsiteError

    @need_login
    def get_accounts(self):
        self.wait_xpath_clickable('//i[@class="iAccount"]')
        self.driver.find_element(By.XPATH, '//i[@class="iAccount"]').click()
        self.wait_xpath_clickable('//a[@href="/adriaClient/app/account/list"]/i')
        self.driver.find_element(By.XPATH, '//a[@href="/adriaClient/app/account/list"]/i').click()
        self.wait_until_is_here(self.accounts_page)
        return self.page.get_accounts()

    @need_login
    def get_account(self, _id):
        for account in self.get_accounts():
            if account.id == _id:
                return account
        self.error_msg = 'ID'
        raise IdNotFoundError

    def go_to_history(self):
        self.wait_xpath_clickable('//i[@class="iAccount"]')
        self.driver.find_element(By.XPATH, '//i[@class="iAccount"]').click()
        self.wait_xpath_clickable('//a[@href="/adriaClient/app/account/statement"]/i')
        self.driver.find_element(By.XPATH, '//a[@href="/adriaClient/app/account/statement"]/i').click()
        self.wait_until_is_here(self.history_page)

    def iter_transactions(self, **kwargs):
        results = []

        table = self.driver.find_element(By.XPATH,
                                         '//*[@id="appRoot"]/div/div[3]/div[2]/div[1]/div/div[1]/div/div/div/div/div/div/div/div[2]/div/div/div/div[2]/div/div/div/div/div/div/table')

        rows = table.find_elements(By.TAG_NAME, 'tr')

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, 'td')
            _id = cells[0].text
            date = cells[1].text
            label = cells[2].text
            # append this tuple to the list
            results.append((_id, date, label))

        return results

    @need_login
    def iter_history(self, _id, **kwargs):
        account = self.get_account(_id)
        self.go_to_history()
        return self.page.get_history(account, **kwargs)

    @need_login
    def get_transactions(self, **kwargs):
        try:
            res = self.iter_transactions(**kwargs)
            return res
        except NoHistoryError:
            return []
