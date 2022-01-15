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

from datetime import datetime
from decimal import Decimal
import hashlib

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction

from woob.browser.selenium import SeleniumPage, VisibleXPath
from selenium.common.exceptions import NoSuchElementException
from woob.scrafi_exceptions import NoHistoryError, WrongCredentialsError


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//form[@id="bloc_ident"]')

    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@id="_userid"]').send_keys(username)
        self.driver.find_element_by_xpath('//input[@id="_pwduser"]').send_keys(password)
        self.driver.find_element_by_xpath('//a[@name="submit"]').click()
        
    def check_error(self):
        try:
            self.driver.find_element_by_xpath('//p[contains(text(), "Votre identifiant est inconnu ou votre mot de passe est faux")]')
            self.browser.error_msg = 'credentials'
            raise WrongCredentialsError
        except NoSuchElementException:
            self.browser.do_login()
            

class AccueilPage(SeleniumPage):
    is_here = VisibleXPath('//p[contains(@class, "_c1 a_titre2 _c1")]')


class VignettePage(SeleniumPage):
    def some():
        pass


class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('//table[@class="_c1 ei_comptescontrats _c1"]')

    def get_accounts(self):
        accounts = []
        elements = self.driver.find_elements_by_xpath('//table[@class="_c1 ei_comptescontrats _c1"]/tbody/tr')[1:]
        for element in elements:
            account = Account()
            account.label = element.find_element_by_xpath('.//td[1]/a/span[1]').text
            account.id = element.find_element_by_xpath('.//td[1]/a/span[4]').text.replace(".", "").strip()
            try:
                account._devise = "(" + element.find_element_by_xpath('.//td[3]/span').text[-3:] + ")"
            except NoSuchElementException:
                account._devise = "(" + element.find_element_by_xpath('.//td[2]/span').text[-3:] + ")"
            for acc in accounts:
                if account.label == acc.label:
                    account.label += ' ' + account._devise
                    acc.label += ' ' + acc._devise
            accounts.append(account)
        return accounts
    
    def go_history(self, account):
        comptes = self.driver.find_elements_by_xpath('//table[@class="_c1 ei_comptescontrats _c1"]/tbody/tr/td[1]/a')
        for compte in comptes:
            number = compte.find_element_by_xpath('./span[4]').text
            number = number.replace('.', '')
            if number == account.id:
                compte.click()
                break


class BMCETransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')


class HistoryPage(SeleniumPage):
    def get_history(self, **kwargs):
        try: 
            self.driver.find_element_by_xpath('//td[contains(text(), "a été enregistrée récemment")]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except NoSuchElementException:
            pass
        
        self.driver.find_element_by_xpath('//a[@title="Rechercher des opérations sur les 6 derniers mois"]').click()
        self.browser.wait_xpath_visible('//table[@class="saisie"]')
        self.driver.find_element_by_xpath('//table[@class="saisie"]/tbody/tr[1]/td[1]/input').send_keys(kwargs['start_date'])
        self.driver.find_element_by_xpath('//table[@class="saisie"]/tbody/tr[1]/td[2]/input').send_keys(kwargs['end_date'])
        time.sleep(3)
        self.driver.find_element_by_xpath('//a[@title="Rechercher"]').click()
        time.sleep(2)

        history = []
        try:
            self.driver.find_element_by_xpath('//td[contains(text(), "Aucune opération ne correspond à votre recherche")]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except NoSuchElementException:
            pass
            
        plus = True
        while plus:
            try:
                self.driver.find_element_by_xpath('//a[@title="Plus d\'opérations"]').click()
                time.sleep(1)
            except NoSuchElementException:
                plus = False
        
        elements = self.driver.find_elements_by_xpath('//table[@class="liste"]/tbody/tr')
        for element in elements:
            tr = BMCETransaction()
            tr.label = element.find_element_by_xpath('.//td[2]/div/div/div[1]').text.strip()
            tr.date = datetime.strptime(element.find_element_by_xpath('.//td[1]').text, '%d/%m/%Y').date()
            try:
                credit = self.decimalism(element.find_element_by_xpath('.//td[4]/span').text)
                debit = self.decimalism(element.find_element_by_xpath('.//td[3]').text)
            except NoSuchElementException:
                debit = self.decimalism(element.find_element_by_xpath('.//td[3]/span').text)
                credit = self.decimalism(element.find_element_by_xpath('.//td[4]').text)
            tr.solde = credit - debit
            tr.amount = tr.solde

            str_2_hash = tr.label + tr.date.strftime('%d/%m/%Y') + str(tr.solde)
            tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

            del (
                tr.url, tr.vdate, tr.rdate, tr.bdate, tr.type, tr.category, tr.card, tr.commission,
                tr.gross_amount, tr.original_amount, tr.original_currency, tr.country, tr.original_commission,
                tr.original_commission_currency, tr.original_gross_amount, tr.investments, tr.raw
                )
                
            history.append(tr)
        return history

    def decimalism(self, stringy):
        if stringy:
            stringy = stringy[1:].replace('MAD', '').replace(',', '.').replace('\xa0', '').replace(' ', '')
            stringy = stringy.replace('+', '').replace('-', '')
        else:
            stringy = '0'
        return Decimal(stringy)