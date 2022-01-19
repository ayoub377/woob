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

from selenium.common.exceptions import NoSuchElementException
from woob.scrafi_exceptions import NoBillError


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//input[@id="_username"]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@id="_username"]').send_keys(username)
        self.driver.find_element_by_xpath('//input[@id="_password"]').send_keys(password)
        self.driver.find_element_by_xpath('//input[@class="btn btn--important d-block-m mdl-js-button  mdl-js-button mdl-js-ripple-effect btn d-block-m--mm btn d-block-m--important submit"]').click()
    
    def check_error(self):
        time.sleep(1)
        try:
            self.driver.find_element_by_xpath('//li[@class="msg-error parsley-customError"]')
            return True
        except NoSuchElementException:
            return False


class InscriptionPage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(),"Inscrivez-vous")]')


class AccueilPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Bienvenue")]')


class OrangeBill(Bill):
    montant = StringField('Montant de la facture')
    date = StringField('Date de la facture')
    pdf = StringField('PDF de la facture')
    hashid = StringField('ScraFi ID')
    
    def __repr__(self):
        return '<%s number=%r date=%r montant=%r tva=%r hashid=%r>' % (
            type(self).__name__, self.number, self.date, self.montant, self.tva, self.hashid)


class BillsPage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(),"Synthèse de facturation")]')

    def get_bills(self, date):
        the_date = datetime.strptime(date, "%d/%m/%Y")
        bills = []
        try:
            self.driver.find_element_by_xpath('//a[@class="link-souligne res-fr mob-mbs mob-disblock app-showmore-synthesis"]').click()
        except NoSuchElementException:
            pass
        
        factures = self.driver.find_elements_by_xpath('//div[@class="table-facture__row pagination-element-synthesis"]')
        if len(factures) == 0:
            self.browser.error_msg = 'nobill'
            raise NoBillError
        
        for facture in factures:         
            facture_date = facture.find_element_by_xpath('.//a[@class="cb-popup cboxElement"]').text
            french_months = {'Janvier': '01',
                'Février': '02',
                'Mars': '03',
                'Avril': '04',
                'Mai': '05',
                'Juin': '06',
                'Juillet': '07',
                'Août': '08',
                'Septembre': '09',
                'Octobre': '10',
                'Novembre': '11',
                'Décembre': '12'}

            parsed_date = datetime.strptime(facture_date[:2] + "/" + french_months[facture_date[3:-5]] + "/" + facture_date[-4:], "%d/%m/%Y")
            if parsed_date < the_date:
                continue
                
            bill = OrangeBill()
            bill.date = parsed_date.strftime('%d/%m/%Y')
            bill.montant = facture.find_element_by_xpath('.//span[@class="number-direction"]').text
            
            bill.number = "IDK"
            bill.pdf = "Icant"
            
            str_2_hash = bill.number + bill.date + bill.montant
            bill.hashid = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()
            
            bills.append(bill)
        return bills