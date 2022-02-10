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


import hashlib, time
from datetime import datetime
from decimal import Decimal

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction

from woob.browser.selenium import SeleniumPage, VisibleXPath
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from woob.scrafi_exceptions import NoHistoryError


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//form[@id="register_form"]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@name="username"]').send_keys(username)
        self.driver.find_element_by_xpath('//input[@name="password"]').click()
        buttons = self.driver.find_elements_by_xpath('//button[contains(@onclick, "appendValue")][not(@disabled)]')
        for i in password:
            for button in buttons:
                if button.text == i:
                    button.click()
        self.driver.find_element_by_xpath('//button[@id="login-button"]').click()


class HomePage(SeleniumPage):
    is_here = VisibleXPath('//p[contains(text(), " Solde ")]')


class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(), " des comptes")]')

    def get_accounts(self):
        accounts = []
        account = Account()
        texte = self.driver.find_element_by_xpath('//p[text()="N°"]').text
        account.id = texte[-16:]
        account.label = texte
        accounts.append(account)
        return accounts

    def go_history_page(self):
        self.driver.find_element_by_xpath('//i[@class="iAccount"]').click()
        self.driver.find_element_by_xpath('//a[@href="/adriaClient/app/account/statement"]/i').click()


class CIHTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')


class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(), "Extrait de compte")]')

    def get_history(self, account, **kwargs):
        self.browser.wait_xpath_clickable('//div[@class="requiredDiv"]')
        self.driver.find_element_by_xpath('//div[@class="requiredDiv"]').click()
        self.browser.wait_xpath_clickable('//select[@name="NumeroCompte"]/option')
        self.driver.find_element_by_xpath('.//option[contains(text(), "%s")]' % account.id)
        
        english_months = {'01': 'January ',
                        '02': 'February ',
                        '03': 'March ',
                        '04': 'April ',
                        '05': 'May ',
                        '06': 'June ',
                        '07': 'July ',
                        '08': 'August ',
                        '09': 'September ',
                        '10': 'October ',
                        '11': 'November ',
                        '12': 'December '}

        _m_y = english_months[kwargs['start_date'][3:5]] + kwargs['start_date'][-4:]
        _day = int(kwargs['start_date'][:2])
        divs = [
            self.driver.find_element_by_xpath('//input[@placeholder="Date de début"]'),
            self.driver.find_element_by_xpath('//input[@placeholder="Date de fin"]')]
        
        for div in divs:
            div.click()
            x = True
            month = self.driver.find_element_by_xpath('//div[@class="react-datepicker"]')

            while x:
                month_name = month.find_element_by_xpath('.//div[@class="react-datepicker__header"]/div[1]').text

                if month_name == _m_y:
                    days = month.find_elements_by_xpath('.//div[@class="react-datepicker__month"]/div/div[not(contains(@class, "--outside-month"))]')
                    for day in days:
                        day_number = int(day.text)
                        
                        if day_number == _day:
                            day.click()
                            _m_y = english_months[kwargs['end_date'][3:5]] + kwargs['end_date'][-4:]
                            _day = int(kwargs['end_date'][:2])
                            x = False
                            break

                else:
                    self.driver.find_element_by_xpath('.//div[@class="react-datepicker__header"]/a[1]').click()

        self.driver.find_element_by_xpath('//div[@class="pull-right col-xs-6"]/button[1]').click()
        trs = []
        try:
            self.browser.wait_xpath_invisible('//div[@class="noDataResult"]')
        except TimeoutException:
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError

        lines = self.driver.find_elements_by_xpath('//table[@class="table"]/tbody[1]/tr')
        for line in lines:
            tr = CIHTransaction()
            
            tr.label = line.find_element_by_xpath('.//td[1]').text
            tr.date = datetime.strptime(line.find_element_by_xpath('.//td[4]').text, '%Y-%m-%d').date()
            
            debit = self.decimalism(line.find_element_by_xpath('.//td[3]/div/div').text)
            credit = self.decimalism(line.find_element_by_xpath('.//td[2]/div/div').text)
            tr.solde = credit - debit
            tr.amount = tr.solde
            
            str_2_hash = tr.label + tr.date.strftime('%Y-%m-%d') + str(tr.solde)
            tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

            del (
                tr.url, tr.vdate, tr.rdate, tr.bdate, tr.type, tr.category, tr.card, tr.commission,
                tr.gross_amount, tr.original_amount, tr.original_currency, tr.country, tr.original_commission,
                tr.original_commission_currency, tr.original_gross_amount, tr.investments, tr.raw
            )
            trs.append(tr)
        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '')
        if stringy == '-' or stringy == '':
            return Decimal('0')  
        else:
            return Decimal(stringy)