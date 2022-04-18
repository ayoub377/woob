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


import time, hashlib, requests, base64, urllib3
from datetime import datetime

from woob.capabilities.bill import Bill
from woob.capabilities.base import StringField
from woob.browser.selenium import SeleniumPage, VisibleXPath

from woob.scrafi_exceptions import NoBillError, WebsiteError
from selenium.common.exceptions import NoSuchElementException
from requests.exceptions import ConnectionError as cnxError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//input[@id="_username"]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@id="_username"]').send_keys(username)
        self.driver.find_element_by_xpath('//input[@id="_password"]').send_keys(password)
        self.driver.find_element_by_xpath('//input[@class="btn btn--important d-block-m mdl-js-button  mdl-js-button mdl-js-ripple-effect btn d-block-m--mm btn d-block-m--important submit"]').click()
    
    def check_error(self):
        time.sleep(1)
        try:
            self.driver.find_element_by_xpath('//span[contains(text(),"Vérifiez le code saisi")]')
            return True
        except NoSuchElementException:
            return False


class InscriptionPage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(),"Inscrivez-vous")]')


class AccueilPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Bienvenue")]')


class OrangeBill(Bill):
    date = StringField('Date de la facture')
    montant = StringField('Montant de la facture')
    pdf = StringField('PDF de la facture')
    
    def __repr__(self):
        return '<%s id=%r number=%r date=%r montant=%r>' % (
            type(self).__name__, self.id, self.number, self.date, self.montant)


class BillsPage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(),"Synthèse de facturation")]')

    def get_bills(self, date):
        the_date = datetime.strptime(date, "%m/%Y")
        bills = []
        urls = []
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
        
        try:
            self.driver.find_element_by_xpath('//a[@class="link-souligne res-fr mob-mbs mob-disblock app-showmore-synthesis"]').click()
        except NoSuchElementException:
            pass
        
        synthesis = self.driver.find_elements_by_xpath('//div[@class="table-facture__row pagination-element-synthesis"]')
        for syn in synthesis:            
            date_element = syn.find_element_by_xpath('.//a[@class="cb-popup cboxElement"]')
            date_text = date_element.text
            try:
                date_object = datetime.strptime(french_months[date_text[3:-5]] + "/" + date_text[-4:], "%m/%Y")
            except KeyError as e:
                self.logger.info(date_text)
                raise e

            bill_date = date_object.strftime('%m/%Y')

            if date_object != the_date:
                continue
            else:
                urel = date_element.get_attribute("href")
                urls.append(urel)
        
        for url in urls:
            self.browser.location(url)
            time.sleep(3)
            factures = self.driver.find_elements_by_xpath('//div[@class="table-facture__row pagination-element"]')
            with requests.Session() as req:
                req.verify = False
                for facture in factures:
                    bill = OrangeBill()
                    
                    bill.date = bill_date
                    bill.number = facture.find_element_by_xpath('.//div[@class="table-facture__cell  w50 table-liste__date "]/span').text
                    bill.montant = facture.find_element_by_xpath('.//div[@class="table-facture__cell  w50 table-liste__montant"]/div/span').text
                    
                    str_2_hash = "orange" + bill.number + bill.date + bill.montant
                    bill.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()
                    
                    pdf_url = facture.find_element_by_xpath('.//div[@class="dropdown-links__contentr simpletoggle-content"]/a').get_attribute("href")
                    x = 0
                    while x < 5:
                        try:
                            response = req.get(pdf_url)
                        except cnxError:
                            x += 1
                            if x == 5:
                                self.browser.error_msg = 'website'
                                raise WebsiteError
                        else:
                            x = 100
                    bill.pdf = base64.b64encode(response.content).decode('utf8')
                    bills.append(bill)
            
        if len(bills) == 0:
            self.browser.error_msg = 'nobill'
            raise NoBillError
        else:
            return bills