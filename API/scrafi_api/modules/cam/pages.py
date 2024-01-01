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


from datetime import datetime
from decimal import Decimal
import hashlib

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction

from woob.browser.selenium import SeleniumPage
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from woob.scrafi_exceptions import NoHistoryError, WebsiteError, WrongCredentialsError


class LoginPage(SeleniumPage):
    def login(self, username, password):
        self.virtual_keyboard(username)
        self.driver.find_element(By.XPATH, '//input[@id="ContentPlaceHolder1_Authentification_Login1_Password"]').send_keys(password)
        self.driver.find_element(By.XPATH, '//input[@id="ContentPlaceHolder1_Authentification_Login1_LoginButton"]').click()

    def virtual_keyboard(self, code):
        keys_dict = {}
        rows = self.driver.find_elements(By.XPATH, '//table[@id="secure"]/tbody/tr')
        for row in rows:
            keys = row.find_elements(By.XPATH, './td')
            for key in keys:
                keys_dict[key.text] = key
        for i in code:
            keys_dict[i].click()

    def check_error(self):
        try:
            self.driver.find_element(By.XPATH, '//span[contains(text(), "Erreur lors de la connexion")]')
            self.browser.error_msg = 'credentials'
            raise WrongCredentialsError
        except NoSuchElementException:
            self.browser.error_msg = 'bank'
            raise WebsiteError


class AccueilPage(SeleniumPage):
    pass


class AccountsPage(SeleniumPage):
    def get_accounts(self):
        accounts = []
        elements = self.driver.find_elements(By.XPATH, '//table[@id="ContentPlaceHolder1_GRV_Compte"]/tbody/tr[@class="content_tab"]')
        for element in elements:
            account = Account()
            account.label = element.find_element(By.XPATH, './td[1]').text
            account.id = element.find_element(By.XPATH, './td[2]').text
            accounts.append(account)
        return accounts


class CamTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')

    def __repr__(self):
        return '<%s id=%r date=%r label=%r solde=%r>' % (
            type(self).__name__, self.id, self.date, self.label, self.solde)


class HistoryPage(SeleniumPage):
    def get_history(self, _id, **kwargs):
        options = self.driver.find_elements(By.XPATH, '//select[@id="ContentPlaceHolder1_ListCompte_Solde"]/option')
        for option in options:
            if _id in option.text:
                option.click()
        self.driver.find_element(By.XPATH, '//input[@id="txtDateOperation_Debut"]').send_keys(kwargs['start_date'])
        self.driver.find_element(By.XPATH, '//input[@id="txtDateOperation_Fin"]').send_keys(kwargs['end_date'])
        self.driver.find_element(By.XPATH, '//html').click()
        self.driver.find_element(By.XPATH, '//input[@id="ContentPlaceHolder1_Btn_Rechercher"]').click()
        try:
            self.browser.wait_xpath_visible('//table[@id="ContentPlaceHolder1_GRV_Historique"]')
        except TimeoutException:
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError

        trs = []
        ids = []
        x = 1
        p = 1
        next_page = True
        while next_page:
            lines = self.driver.find_elements(By.XPATH, '//table[@id="ContentPlaceHolder1_GRV_Historique"]/tbody/tr[@class="content_tab"]')
            for line in lines:
                tr = CamTransaction()
                tr.label = line.find_element(By.XPATH, './td[2]').text
                tr.date = datetime.strptime(line.find_element(By.XPATH, './td[1]').text, '%d/%m/%Y').date()

                debit = self.decimalism(line.find_element(By.XPATH, './td[3]').text)
                credit = self.decimalism(line.find_element(By.XPATH, './td[4]').text)
                tr.solde = credit - debit

                str_2_hash = tr.label + tr.date.strftime('%d/%m/%Y') + str(tr.solde)
                tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

                x = 1
                while tr.id in ids:
                    str_to_hash = str_2_hash + str(x)
                    tr.id = hashlib.md5(str_to_hash.encode("utf-8")).hexdigest()
                    x += 1
                ids.append(tr.id)
                trs.append(tr)

            pages = self.driver.find_elements(By.XPATH, '//tr[@class="pgr"]/td/table/tbody/tr/td')
            if len(pages) == 0:
                next_page = False
            else :
                p += 1
                try:
                    self.driver.find_element(By.XPATH, f'//a[contains(text(), "{p}")]').click()
                    self.browser.wait_xpath_visible(f'//tr[@class="pgr"]/td/table/tbody/tr/td/span[contains(text(), "{p}")]')
                except NoSuchElementException:
                    try:
                        self.driver.find_element(By.XPATH, f'//a[contains(@href, "Page${p}")]').click()
                        self.browser.wait_xpath_visible(f'//tr[@class="pgr"]/td/table/tbody/tr/td/span[contains(text(), "{p}")]')
                    except NoSuchElementException:
                        next_page = False
        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '.')
        stringy = stringy.replace('+', '').replace('-', '')
        if stringy == '-' or stringy == '':
            return Decimal('0')  
        else:
            return Decimal(stringy)
