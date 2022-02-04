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
import time
from selenium.common.exceptions import TimeoutException

from woob.browser import URL, need_login
from woob.browser.selenium import SeleniumBrowser, webdriver
from woob.scrafi_exceptions import IdNotFoundError, WebsiteError

from .pages import LoginPage, ChoicePage, HomePage, AccountsPage, HistoryPage


class CDMBrowser(SeleniumBrowser):
    BASEURL = 'https://ebanking.cdm.co.ma'

    if 'linux' in sys.platform:
        from xvfbwrapper import Xvfb
        vdisplay = Xvfb()
        vdisplay.start()

    HEADLESS = False

    DRIVER = webdriver.Chrome

    login_page = URL(r'/', LoginPage)
    choice_page = URL(r'/authen/authentication', ChoicePage)
    home_page = URL(r'/ebank/home', HomePage)
    accounts_page = URL(r'/ebank/accounts/', AccountsPage)
    history_page = URL(r'/ebank/accounts/0/transactions/booked', HistoryPage)
    
    error_msg = ''

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        super(CDMBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.login_page.go()
        try:
            self.wait_until_is_here(self.login_page)
            self.page.login(self.username, self.password)
            if self.home_page.is_here():
                self.logged = True
            elif self.choice_page.is_here():
                self.page.choose()
                time.sleep(10)
                self.home_page.go()
                self.wait_until_is_here(self.home_page)
                self.logged = True
            elif self.login_page.is_here():
                self.page.check_error()
        except TimeoutException:
            self.error_msg = 'bank'
            raise WebsiteError

    @need_login
    def get_accounts(self):
        self.accounts_page.go()
        self.wait_until_is_here(self.accounts_page)
        return self.page.get_accounts()

    @need_login
    def get_account(self, _id):
        for account in self.get_accounts():
            if account.id == _id:
                return account
        self.error_msg = 'ID'
        raise IdNotFoundError

    @need_login
    def iter_history(self, _id, **kwargs):
        account = self.get_account(_id)
        self.accounts_page.stay_or_go()
        self.wait_until_is_here(self.accounts_page)
        self.page.go_history_page(account.id)
        self.wait_until_is_here(self.history_page)
        return self.page.get_history(**kwargs)