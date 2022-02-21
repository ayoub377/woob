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

from woob.browser.selenium import SeleniumPage, VisibleXPath
from woob.capabilities.bill import Bill
from woob.capabilities.base import StringField

from woob.scrafi_exceptions import NoBillError
from selenium.common.exceptions import NoSuchElementException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="_58_login"]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//*[@id="_58_login"]').send_keys(username)
        self.driver.find_element_by_xpath('//*[@id="_58_password"]').send_keys(password)
        self.driver.find_element_by_xpath('//*[@id="_58_fm"]/div/span/span/input').click()
    
    def check_error(self):
        time.sleep(1)
        try:
            self.driver.find_element_by_xpath('//div[@class="portlet-msg-error"]')
            return True
        except NoSuchElementException:
            return False

        
class AccueilPage(SeleniumPage):
    is_here = VisibleXPath('//span[contains(text(),"Accueil")]')


class LydecBill(Bill):
    date = StringField('Date de la facture')
    montant = StringField('Montant de la facture')
    pdf = StringField('PDF de la facture')
    
    def __repr__(self):
        return '<%s id=%r number=%r date=%r montant=%r>' % (
            type(self).__name__, self.id, self.number, self.date, self.montant)


class BillsPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Mes factures")]')

    def get_bills(self, date):
        the_date = datetime.strptime(date, "%m/%Y")
        month = the_date.strftime('%m')
        year = the_date.strftime('%Y')
        bills = []
        
        contrats = self.driver.find_elements_by_xpath('//select[@name="polNum"]/option')
        x = len(contrats)
        for i in range(x):         
            self.driver.find_element_by_xpath('//select[@name="polNum"]/option[%s]' % str(i+1)).click()
            self.driver.find_element_by_xpath('//*[@name="moisD"]/option[@value="%s"]' % month).click()
            self.driver.find_element_by_xpath('//*[@name="anneeD"]/option[@value="%s"]' % year).click()
            self.driver.find_element_by_xpath('//*[@id="submit"]').click()
            time.sleep(1)

            try:
                self.driver.find_element_by_xpath('//table[@id="thetable"]/tbody/tr')
            except NoSuchElementException:
                continue
            
            trs = self.driver.find_elements_by_xpath('//table[@id="thetable"]/tbody/tr')
            for tr in trs:
                bill = LydecBill()

                prd_fact = tr.find_element_by_xpath('./td[2]').text.rstrip()
                parsed_date = datetime.strptime(prd_fact, "%Y%m")
                bill.date= parsed_date.strftime("%m/%Y")
                if parsed_date != the_date:
                    continue
                bill.number = tr.find_element_by_xpath('./td[1]').text.rstrip()
                bill.montant = tr.find_element_by_xpath('./td[3]').text

                str_2_hash = "lydec" + bill.number + bill.date + bill.montant
                bill.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

                url = tr.find_element_by_xpath('./td[7]/a').get_attribute("href")
                response = requests.get(url, verify=False)
                bill.pdf = base64.b64encode(response.content).decode('utf8')

                bills.append(bill)
                
        if len(bills) == 0:
            self.browser.error_msg = 'nobill'
            raise NoBillError
        else:
            return bills