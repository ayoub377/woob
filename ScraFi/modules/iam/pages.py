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


import time, hashlib
from datetime import datetime

from woob.capabilities.bill import Bill
from woob.capabilities.base import StringField
from woob.browser.selenium import SeleniumPage, VisibleXPath

from woob.scrafi_exceptions import NoBillError
from selenium.common.exceptions import NoSuchElementException


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Pour accéder à votre compte, veuillez vous identifier.")]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@id="txtEmail"]').send_keys(username)
        self.driver.find_element_by_xpath('//input[@id="txtPassword"]').send_keys(password)
        self.driver.find_element_by_xpath('//input[@id="lnkBtnConnex"]').click()
    
    def check_error(self):
        time.sleep(1)
        try:
            self.driver.find_element_by_xpath('//*[contains(text(),"Votre mot de passe ou e-mail est incorrect")]')
            return True
        except NoSuchElementException:
            return False


class AccueilPage(SeleniumPage):
    is_here = VisibleXPath('//span[contains(text(),"Bienvenue sur votre espace client")]')


class IamBill(Bill):
    montant = StringField('Montant de la facture')
    date = StringField('Date de la facture')
    pdf = StringField('PDF de la facture')
    hashid = StringField('ScraFi ID')
    
    def __repr__(self):
        return '<%s number=%r date=%r montant=%r hashid=%r>' % (
            type(self).__name__, self.number, self.date, self.montant, self.hashid)


class BillsPage(SeleniumPage):
    is_here = VisibleXPath('//h2[@class="historique"]')

    def get_bills(self, date):
        the_date = datetime.strptime(date, "%d/%m/%Y")
        bills = []
        french_months = {'janvier': '01',
            'février': '02',
            'mars': '03',
            'avril': '04',
            'mai': '05',
            'juin': '06',
            'juillet': '07',
            'août': '08',
            'septembre': '09',
            'octobre': '10',
            'novembre': '11',
            'décembre': '12'}
        
        factures = self.driver.find_elements_by_xpath('//div[@class="table table-bordered"]/tbody/tr')
        if len(factures) == 0:
            self.browser.error_msg = 'nobill'
            raise NoBillError
        
        for facture in factures:
            bill = IamBill()
            
            facture_date = facture.find_element_by_xpath('.//td[2]/span').text.split()
            parsed_date = datetime.strptime(french_months[facture_date[0]] + "/" + facture_date[1], "%m/%Y")
            bill.date = parsed_date.strftime('%m/%Y')
            if parsed_date < the_date:
                continue
            
            bill.montant = facture.find_element_by_xpath('.//td[3]').text
            str_2_hash = "maroctelecom" + bill.date + bill.montant
            bill.hashid = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()
            
            url = facture.find_element_by_xpath('.//td[1]/a').get_attribute("href")
            print(url)
            
            bill.pdf = "Idk yet"
            
            bills.append(bill)
            
        if len(bills) == 0:
            self.browser.error_msg = 'nobill'
            raise NoBillError
        else:
            return bills