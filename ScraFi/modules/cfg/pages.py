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
import time
import hashlib

from datetime import datetime
from decimal import Decimal

from woob.capabilities.base import DecimalField, StringField
from woob.capabilities.bank.base import Account, Transaction
from woob.browser.selenium import SeleniumPage, VisibleXPath
from selenium.common.exceptions import NoSuchElementException
from woob.scrafi_exceptions import NoHistoryError, WebsiteError, WrongCredentialsError


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//form[@id="formPass"]')

    def login(self, username, password):
        self.driver.execute_script("""
                        document.getElementsByName("USERNAME")[0].value = "%s"
                        document.getElementsByName("PASSWORD")[0].value = "%s"
                        document.LOGINFORM.submit()
                        """ % (username, password))

    def check_error(self):
        try:
            self.driver.find_element_by_xpath('//div[@class="Indice"]')
            self.browser.error_msg = 'credentials'
            raise WrongCredentialsError
        except NoSuchElementException:
            self.browser.error_msg = 'bank'
            raise WebsiteError
    

class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(), "Aperçu de vos comptes")]')

    def get_accounts(self):
        accounts = []
        account = Account()
        account.id = self.driver.find_element_by_xpath('//*[@id="come$rep_srv_acc_view"]').get_attribute('text')[6:34].replace(" ", "")
        account.label = 'Unknown Label'
        accounts.append(account)
        return accounts

    def go_history_page(self):
        self.driver.find_element_by_xpath('//*[@id="come$rep_srv_acc_view"]').click()


class CFGTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')
    hashid = StringField('Scrafi ID')

    def __repr__(self):
        return '<%s hashid=%r date=%r label=%r solde=%r>' % (
            type(self).__name__, self.hashid, self.date, self.label, self.solde)


class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('//td[contains(text(), "Nº de compte CFG")]')

    def get_history(self, **kwargs):
        self.driver.find_element_by_xpath('//input[@id="wr_inclTempBookings"]').click()
        self.driver.find_element_by_xpath('//input[@id="wr_from_date"]').clear()
        self.driver.find_element_by_xpath('//input[@id="wr_from_date"]').send_keys(kwargs['start_date'].replace('/', '.'))
        self.driver.find_element_by_xpath('//input[@id="wr_to_date"]').clear()
        self.driver.find_element_by_xpath('//input[@id="wr_to_date"]').send_keys(kwargs['end_date'].replace('/', '.'))
        self.driver.find_element_by_xpath('//input[@name="action_show"]').click()
        time.sleep(1)

        trs = []
        hashids = []
        try:
            self.driver.find_element_by_xpath('//td[@class="noleftborder firstCell lastCell"]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except NoSuchElementException:
            pass

        lines = self.driver.find_elements_by_xpath('//table[@class="tree font-small"]/tbody/tr')[3:]

        for line in lines:
            if line.find_element_by_xpath('.//td[1]').text == 'Total':
                break

            tr = CFGTransaction()
            try:
                tr.label = line.find_element_by_xpath('.//td[4]/a').text
            except NoSuchElementException:
                tr.label = line.find_element_by_xpath('.//td[4]').text

            tr.date = datetime.strptime(line.find_element_by_xpath('.//td[2]').text, '%d.%m.%Y').date()
            
            debit = self.decimalism(line.find_element_by_xpath('.//td[5]').text)
            credit = self.decimalism(line.find_element_by_xpath('.//td[6]').text)
            tr.solde = credit - debit
            
            str_2_hash = tr.label + tr.date.strftime('%d/%m/%Y') + str(tr.solde)
            tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

            x = 1
            while tr.hashid in hashids:
                str_to_hash = str_2_hash + str(x)
                tr.hashid = hashlib.md5(str_to_hash.encode("utf-8")).hexdigest()
                x += 1

            hashids.append(tr.hashid)
            trs.append(tr)
        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '')
        return Decimal('0') if stringy == '' else Decimal(stringy)