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
import hashlib, time
from hmac import trans_36

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction
from woob.browser.selenium import SeleniumPage, VisibleXPath
from woob.scrafi_exceptions import NoHistoryError, WebsiteError

from selenium.common.exceptions import NoSuchElementException
from selenium import webdriver
from selenium.webdriver.common.keys import Keys


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="loginForm:btnLogin"]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@id="loginForm:txtLoginId"]').send_keys(username)
        self.driver.find_element_by_xpath('//input[@id="loginForm:kbLoginPassword"]').send_keys(password)
        webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        self.driver.find_element_by_xpath('//button[@id="loginForm:btnLogin"]').click()
        
    def check_error(self):
        try:
            self.driver.find_element_by_xpath('//span[text()="Identifiant ou mot de passe invalide."]')
            return True
        except NoSuchElementException:
            self.browser.error_msg = 'bank'
            raise WebsiteError
        

class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('//h3[text()="Mes comptes"]')

    def get_accounts(self):
        accounts = []
        time.sleep(3)
        accounts_list = self.driver.find_elements_by_xpath('//tbody[@id="frmMainDashboard:tbAccountsSummary:tblTransactionAccountsSummary_data"]/tr')
        for acc in accounts_list:
            account = Account()
            account.id = acc.find_element_by_xpath('./td[1]/a/span').text
            account.label = acc.find_element_by_xpath('./td[2]/span[2]').text
            accounts.append(account)
        return accounts

    def go_history_page(self):
        self.driver.find_element_by_xpath('//li[@id="menuform:sm_0"]/a').click()
        time.sleep(1)
        self.driver.find_element_by_xpath('//li[@id="menuform:sm_FNCEBCW040"]/a').click()
        time.sleep(1)


class AkhdarTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')


class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('//form[@id="frmTransactionshistory"]')

    def get_history(self, _id, **kwargs):
        start = kwargs['start_date'].replace('/', '-')
        end = kwargs['end_date'].replace('/', '-')

        self.driver.find_element_by_xpath('//label[@id="frmTransactionshistory:ddlAccountType_label"]').click()
        time.sleep(1)
        self.driver.find_element_by_xpath('//li[@id="frmTransactionshistory:ddlAccountType_1"]').click()
        time.sleep(6)
        self.driver.find_element_by_xpath('//label[@id="frmTransactionshistory:customerAccounts_label"]').click()
        time.sleep(1)
        self.driver.find_element_by_xpath('//li[contains(text(), "%s")]' % _id).click()
        time.sleep(2)
        self.driver.find_element_by_xpath('//div[@class="ui-radiobutton-box ui-widget ui-corner-all ui-state-default"]').click()
        time.sleep(8)
        self.driver.find_element_by_xpath('//input[@id="frmTransactionshistory:fromDate_input"]').send_keys(start)
        self.driver.find_element_by_xpath('//input[@id="frmTransactionshistory:toDate_input"]').send_keys(end)
        self.driver.find_element_by_xpath('//button[@id="frmTransactionshistory:btnSearch"]').click()
        time.sleep(10)

        try:
            self.driver.find_element_by_xpath('//label[@id="frmTransactionshistory:lblNoResult"]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except NoSuchElementException:
            pass

        trs = []
        pages = True
        while pages:
            lines = self.driver.find_elements_by_xpath('//tbody[@id="frmTransactionshistory:bcSaving:savingDetails_data"]/tr')
            for line in lines:
                tr = AkhdarTransaction()

                tr.label = line.find_element_by_xpath('./td[2]/label').text
                tr.date = datetime.strptime(line.find_element_by_xpath('./td[1]/label').text, '%d-%m-%Y').date()

                debit = self.decimalism(line.find_element_by_xpath('./td[3]/label').text)
                credit = self.decimalism(line.find_element_by_xpath('.//td[4]/label').text)
                tr.solde = credit - debit
                tr.amount = tr.solde
                print(tr.solde)

                str_2_hash = tr.label + tr.date.strftime('%d/%m/%Y') + str(tr.solde)
                tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

                trs.append(tr)

                if lines.index(line) == len(lines)-1:
                    print("------------------------")
                    webdriver.ActionChains(self.driver).send_keys(Keys.SPACE).perform()
                    time.sleep(3)
                    try:
                        self.driver.find_element_by_xpath('//span[@class="ui-paginator-next ui-state-default ui-corner-all"]').click()
                        "ui-paginator-next ui-state-default ui-corner-all"
                        print("------>>>> next page")
                        time.sleep(5)
                    except NoSuchElementException:
                        print('cannot find next <--------------------------------')
                        pages = False

        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '.')
        stringy = stringy.replace('+', '').replace('-', '')
        if stringy == '-' or stringy == '':
            return Decimal('0')  
        else:
            return Decimal(stringy)
