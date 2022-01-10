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


import sys, hashlib
from decimal import Decimal

from woob.browser import URL, need_login
from woob.browser.selenium import SeleniumBrowser, webdriver
from woob.capabilities.bill import Detail

from woob.scrafi_exceptions import WebsiteError, WrongCredentialsError
from selenium.common.exceptions import TimeoutException

from .pages import LoginPage, AccueilPage, ProfilePage, SubscriptionPage, BillsPage, DocumentsPage


class LydecBrowser(SeleniumBrowser):
    BASEURL = 'https://client.lydec.ma/site'

    if 'linux' in sys.platform:
        from xvfbwrapper import Xvfb
        vdisplay = Xvfb()
        vdisplay.start()

    HEADLESS = False

    DRIVER = webdriver.Chrome

    login_page = URL(r'/fr/web/lydec', LoginPage)
    accueil_page = URL(r'/fr/web/lydec/accueil', AccueilPage)
    profile_page = URL('/fr/web/lydec/infos-client', ProfilePage)
    subscription_page = URL(r'/fr/web/lydec/mes-contrats', SubscriptionPage)
    bills_page = URL(r'/fr/web/lydec/mes-impayes', BillsPage)
    documents_page = URL(r'/fr/web/lydec/mes-factures-multisites', DocumentsPage)

    error_msg = ''

    def __init__(self, config, *args, **kwargs):
        self.config = config
        self.username = self.config['login'].get()
        self.password = self.config['password'].get()
        super(LydecBrowser, self).__init__(*args, **kwargs)

    def do_login(self):
        self.login_page.stay_or_go()
        try:
            self.wait_until_is_here(self.login_page)
            self.page.login(self.username, self.password)
            try:
                self.wait_until_is_here(self.accueil_page)
                self.logged = True
            except TimeoutException: 
                if self.page.check_error():
                    self.error_msg = "credentials"
                    raise WrongCredentialsError
        except TimeoutException:
            self.error_msg = 'website'
            raise WebsiteError

    @need_login
    def connect(self):
        listash = []
        str_2_hash = 'lydec' + self.username + self.password
        hash_id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()
        listash.append(hash_id)
        return listash

    @need_login
    def get_profile(self):
        self.profile_page.stay_or_go()
        self.wait_until_is_here(self.profile_page)
        return self.page.get_profile()

    @need_login
    def iter_subscriptions(self):
        self.subscription_page.stay_or_go()
        self.wait_until_is_here(self.subscription_page)
        return self.page.get_subscriptions()

    @need_login
    def get_bills(self):
        self.bills_page.stay_or_go()
        self.wait_until_is_here(self.bills_page)
        return self.page.get_bills()

    @need_login
    def iter_documents(self, sub_id):
        self.bills_page.stay_or_go()
        self.wait_until_is_here(self.bills_page)
        for i in self.page.get_bills(sub_id):
            self.documents_page.stay_or_go()
            self.wait_until_is_here(self.documents_page)
            yield self.page.get_documents(i._sub_id, i.duedate)

    @need_login
    def get_details(self, sub):
        det = LydecDetail()
        det.id = sub.id
        det.label = sub.label
        det.infos = sub.address
        det.price = Decimal(sub.impaye)
        det.currency = 'MAD'
        det.quantity = Decimal(sub.conso[:-5])
        det.unit = sub.conso[-5:]
        return det
    
    
class LydecDetail(Detail):
    def __repr__(self):
        return '<%s id=%r label=%r infos=%r price=%r currency=%r quantity=%r unit=%r>' % (
        type(self).__name__, self.id, self.label, self.infos, self.price, self.currency, self.quantity, self.unit
    )
