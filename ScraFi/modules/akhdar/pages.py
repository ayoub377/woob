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

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction
from woob.browser.selenium import SeleniumPage, VisibleXPath
from woob.scrafi_exceptions import NoHistoryError, WebsiteError

from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="loginForm:btnLogin"]')
    
    def login(self, username, password):
        self.driver.find_element(By.XPATH, '//input[@id="loginForm:txtLoginId"]').send_keys(username)
        self.driver.find_element(By.XPATH, '//input[@id="loginForm:kbLoginPassword"]').send_keys(password)
        webdriver.ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
        self.driver.find_element(By.XPATH, '//button[@id="loginForm:btnLogin"]').click()
        
    def check_error(self):
        try:
            self.driver.find_element(By.XPATH, '//span[text()="Identifiant ou mot de passe invalide."]')
            return True
        except NoSuchElementException:
            self.browser.error_msg = 'bank'
            raise WebsiteError
        

class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('//h3[text()="Mes comptes"]')

    def get_accounts(self):
        accounts = []
        time.sleep(3)
        try:
            accounts_list = self.driver.find_elements(By.XPATH, '//tbody[@id="frmMainDashboard:tbAccountsSummary:tblTransactionAccountsSummary_data"]/tr')
        except NoSuchElementException:
            try:
                self.driver.find_element(By.XPATH, '//span[text()="No records found."]')
                self.browser.accounts_page.go()
                self.browser.get_accounts()
            except NoSuchElementException:
                raise WebsiteError
        else:
            for acc in accounts_list:
                account = Account()
                account.id = acc.find_element(By.XPATH, './td[1]/a/span').text
                account.label = acc.find_element(By.XPATH, './td[2]/span[2]').text
                accounts.append(account)
            return accounts


    def go_history_page(self):
        self.driver.find_element(By.XPATH, '//li[@id="menuform:sm_0"]/a').click()
        self.browser.wait_xpath_clickable('//li[@id="menuform:sm_FNCEBCW040"]/a')
        self.driver.find_element(By.XPATH, '//li[@id="menuform:sm_FNCEBCW040"]/a').click()


class AkhdarTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')

    def __repr__(self):
        return '<%s id=%r date=%r label=%r solde=%r>' % (
            type(self).__name__, self.id, self.date, self.label, self.solde)


class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('//form[@id="frmTransactionshistory"]')
    ids = []

    def get_history(self, _id, **kwargs):
        start = kwargs['start_date'].replace('/', '-')
        end = kwargs['end_date'].replace('/', '-')

        self.browser.wait_xpath_clickable('//label[@id="frmTransactionshistory:ddlAccountType_label"]')
        self.driver.find_element(By.XPATH, '//label[@id="frmTransactionshistory:ddlAccountType_label"]').click()
        self.driver.find_element(By.XPATH, '//li[@id="frmTransactionshistory:ddlAccountType_1"]').click()
        time.sleep(6)
        self.driver.find_element(By.XPATH, '//label[@id="frmTransactionshistory:customerAccounts_label"]').click()
        self.browser.wait_xpath_clickable('//li[contains(text(), "%s")]' % _id)
        self.driver.find_element(By.XPATH, '//li[contains(text(), "%s")]' % _id).click()
        self.browser.wait_xpath_clickable('//div[@class="ui-radiobutton-box ui-widget ui-corner-all ui-state-default"]')
        self.driver.find_element(By.XPATH, '//div[@class="ui-radiobutton-box ui-widget ui-corner-all ui-state-default"]').click()

        self.browser.wait_xpath_visible('//input[@id="frmTransactionshistory:fromDate_input"][@aria-disabled="false"]')
        self.driver.find_element(By.XPATH, '//input[@id="frmTransactionshistory:fromDate_input"]').send_keys(start)
        self.driver.find_element(By.XPATH, '//input[@id="frmTransactionshistory:toDate_input"]').send_keys(end)
        self.driver.find_element(By.XPATH, '//button[@id="frmTransactionshistory:btnSearch"]').click()

        try:
            self.browser.wait_xpath_visible('//label[@id="frmTransactionshistory:lblNoResult"]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except TimeoutException:
            pass

        trs = self.get_transactions()
        i = 1
        x = True
        while x:
            try:
                self.browser.wait_xpath_visible('//span[@class="ui-paginator-pages"]/span')
            except TimeoutException:
                x = False
                break
            else:
                pages = self.driver.find_elements(By.XPATH, '//span[@class="ui-paginator-pages"]/span')
                try:
                    total_pages = int(pages[-1].text)
                except Exception as e:
                    self.logger.info(len(pages))
                    raise e

                if i != total_pages:
                    self.driver.find_element(By.XPATH, '//span[@class="ui-paginator-pages"]/span[contains(text(), "%s")]' % str(i+1)).click()
                    self.browser.wait_xpath_visible('//span[@class="ui-paginator-page ui-state-default ui-corner-all ui-state-active"][text()="%s"]' % str(i+1))
                    trs += self.get_transactions()
                    i += 1
                else:
                    x = False
                    break
        return trs

    def get_transactions(self):
        transactions = []
        lines = self.driver.find_elements(By.XPATH, '//tbody[@id="frmTransactionshistory:bcSaving:savingDetails_data"]/tr')
        for line in lines:
            tr = AkhdarTransaction()
            try:
                tr.label = line.find_element(By.XPATH, './td[2]/label').text
                tr.date = datetime.strptime(line.find_element(By.XPATH, './td[1]/label').text, '%d-%m-%Y').date()
                debit = self.decimalism(line.find_element(By.XPATH, './td[3]/label').text)
                credit = self.decimalism(line.find_element(By.XPATH, './/td[4]/label').text)
                tr.solde = credit - debit
            except StaleElementReferenceException:
                pass

            str_2_hash = tr.label + tr.date.strftime('%d/%m/%Y') + str(tr.solde)
            tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

            x = 1
            while tr.id in self.ids:
                str_to_hash = str_2_hash + str(x)
                tr.id = hashlib.md5(str_to_hash.encode("utf-8")).hexdigest()
                x += 1

            self.ids.append(tr.id)
            transactions.append(tr)
        return transactions

    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '.')
        stringy = stringy.replace('+', '').replace('-', '')
        if stringy == '-' or stringy == '':
            return Decimal('0')  
        else:
            return Decimal(stringy)