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
from selenium.common.exceptions import TimeoutException
from woob.scrafi_exceptions import IdNotFoundError, WebsiteError, WrongCredentialsError

from .pages import LoginPage, AccountsPage, HistoryPage


class AkhdarBrowser(SeleniumBrowser):
    BASEURL = 'https://www.alakhdarbank.net'

    if 'linux' in sys.platform:
        from xvfbwrapper import Xvfb
        vdisplay = Xvfb(width=2920, height=1080)
        vdisplay.start()
    
    HEADLESS = False

    DRIVER = webdriver.Chrome

    login_page = URL(r'/ETHIX-Net/customer-login.xhtml', LoginPage)
    accounts_page = URL(r'/ETHIX-Net/index.xhtml', AccountsPage)
    history_page = URL(r'/ETHIX-Net/index.xhtml', HistoryPage)

    error_msg = ''
    
    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        super(AkhdarBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.login_page.stay_or_go()
        try:
            self.wait_until_is_here(self.login_page)
            self.page.login(self.username, self.password)
            try:
                self.wait_until_is_here(self.accounts_page)
                self.logged = True
            except TimeoutException:
                if self.page.check_error():
                    self.error_msg = 'credentials'
                    raise WrongCredentialsError
        except TimeoutException:
            self.error_msg = 'bank'
            raise WebsiteError

    @need_login
    def get_accounts(self):
        self.accounts_page.stay_or_go()
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
        self.get_account(_id)
        self.accounts_page.stay_or_go()
        self.page.go_history_page()
        self.wait_until_is_here(self.history_page)
        return self.page.get_history(_id, **kwargs)