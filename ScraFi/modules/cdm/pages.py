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


import sys, math, hashlib, pytesseract, base64
from PIL import Image
import numpy as np
from io import BytesIO

from datetime import datetime
from decimal import Decimal

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction

from woob.browser.selenium import SeleniumPage, VisibleXPath
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from woob.scrafi_exceptions import NoHistoryError, WrongCredentialsError

np.set_printoptions(threshold=sys.maxsize)

if 'win' in sys.platform:
    tess_path = 'C:/Program Files/Tesseract-OCR/tesseract.exe'
elif 'linux' in sys.platform:
    tess_path = '/usr/bin/tesseract'
pytesseract.pytesseract.tesseract_cmd = tess_path


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//form[@id="formP1"]')

    def translator(self, matrix, password):
        translated = ''
        for i in password:
            translated += matrix[i]
        return translated
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//input[@name="user"]').send_keys(username)
        matrix = {}
        numbers = self.driver.find_elements_by_xpath('//*[@id="secureCode"]/table[1]/tbody/tr/td/a')
        for number in numbers:            
            img = number.find_element_by_xpath('.//img')
            src = img.get_attribute('src')[-5]

            img_base64 = self.driver.execute_async_script("""
                            var ele = arguments[0], callback = arguments[1];
                            ele.addEventListener('load', function fn(){
                                ele.removeEventListener('load', fn, false);
                                var cnv = document.createElement('canvas');
                                cnv.width = 54; cnv.height = 64;
                                cnv.getContext('2d').drawImage(this, 0, 0);
                                callback(cnv.toDataURL('image/jpeg').substring(22));
                            }, false);
                            ele.dispatchEvent(new Event('load'));
                            """, img) 

            img_n = Image.open(BytesIO(base64.b64decode(img_base64)))
            matrix[self.img_to_number(img_n)] = src

        mdp = self.translator(matrix, password)
        for n in mdp:
            self.driver.find_element_by_xpath('//a[contains(@onclick, ",\'%s\');return")]' % n).click()
        self.driver.find_element_by_xpath('//button[@type="submit"]').click()

    def img_to_number(self, img):
        img = np.array(img)
        img = img[15:45, 13:38]
        number = pytesseract.image_to_string(img, config='--psm 8 --oem 0 -c tessedit_char_whitelist=0123456789').replace('\n\x0c', '').strip()
        return number
    
    def check_error(self):
        try:
            self.driver.find_element_by_xpath('//h3[contains(text(), "authentification a échoué")]')
            self.browser.error_msg = 'credentials'
            raise WrongCredentialsError
        except NoSuchElementException:
            try:
                self.driver.find_element_by_xpath('//label[@id="user-error"]')
                self.browser.error_msg = 'credentials'
                raise WrongCredentialsError
            except NoSuchElementException:
                try:
                    self.driver.find_element_by_xpath('//label[@id="pass-error"]')
                    self.browser.error_msg = 'credentials'
                    raise WrongCredentialsError
                except NoSuchElementException:
                    self.browser.do_login()
        

class ChoicePage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(), "Cliquer sur le service de votre choix")]')

    def choose(self):
        self.driver.find_element_by_xpath('//a[contains(@href, "https://ebanking.cdm.co.ma/")]').click()


class HomePage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(), "Synthèse de mes comptes")]')


class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('//h3[contains(text(), "Liste des comptes")]')

    def get_accounts(self):
        accounts = []
        remember_label = ''
        comptes = self.driver.find_elements_by_xpath('//*[@id="dataTable"]/tbody/tr')
        for compte in comptes:
            if not compte.get_attribute('id'):
                account = Account()
                account.id = compte.find_element_by_xpath('.//td[1]/span[1]').get_attribute('data-acc-id')
                devise = compte.find_element_by_xpath('.//td[1]/span[1]').get_attribute('title')
                account._devise = "(" + devise.rsplit("(")[1]
                try:
                    remember_label = account.label = compte.find_element_by_xpath('.//td[1]/div[1]/div').text
                except NoSuchElementException:
                    account.label = remember_label
                for acc in accounts:
                    if account.label == acc.label:
                        account.label += ' ' + account._devise
                        acc.label += ' ' + acc._devise
                accounts.append(account)
        return accounts

    def go_history_page(self, acc_id):
        comptes = self.driver.find_elements_by_xpath('//*[@id="dataTable"]/tbody/tr')
        for compte in comptes:
            rib = compte.find_element_by_xpath('.//td[1]/span[1]').get_attribute('data-acc-id')
            if rib == acc_id:
                compte.find_element_by_xpath('.//td[1]/div[2]/a[2]').click()
                break
            else:
                continue


class CDMTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')


class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="tabContainer"]/div[1]/ul/ul/a[2]')

    def get_history(self, **kwargs):
        self.driver.find_element_by_xpath('//*[@id="filter_expander"]').click()
        start_input = self.driver.find_element_by_xpath('//input[@name="dateFilterFrom"]')
        self.driver.execute_script('arguments[0].setAttribute("value", "%s")' % kwargs['start_date'], start_input)
        end_input = self.driver.find_element_by_xpath('//input[@name="dateFilterTo"]')
        self.driver.execute_script('arguments[0].setAttribute("value", "%s")' % kwargs['end_date'], end_input)
        self.driver.find_element_by_xpath('//div[@id="button_filter_search"]').click()

        trs = []
        total_text = self.driver.find_element_by_xpath('//*[@id="filter_div"]/form/span').text
        if int(total_text[8:]) == 0:
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError

        tbody = math.ceil(int(total_text[8:])/30)
        x = 1
        self.driver.find_element_by_xpath('//*[@id="acc-trans-table-booked/"]/tbody').click()
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        while x <= tbody:
            lines = self.driver.find_elements_by_xpath('//*[@id="acc-trans-table-booked/"]/tbody[%s]/tr' % x)
            for line in lines:
                tr = CDMTransaction()
                tr.label = line.find_element_by_xpath('.//td[5]/span').text
                tr.date = datetime.strptime(line.find_element_by_xpath('.//td[3]/div').text, '%d/%m/%Y').date()

                try :
                    debit = self.decimalism(line.find_element_by_xpath('.//td[6]/span/bdo').text)
                    credit = self.decimalism(line.find_element_by_xpath('.//td[7]').text)
                except NoSuchElementException:
                    debit = self.decimalism(line.find_element_by_xpath('.//td[6]').text)
                    credit = self.decimalism(line.find_element_by_xpath('.//td[7]/span/bdo').text)
                    
                tr.solde = credit - debit
                tr.amount = tr.solde

                str_2_hash = tr.label + tr.date.strftime('%d/%m/%Y') + str(tr.solde)
                tr.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()
                    
                del (
                    tr.url, tr.vdate, tr.rdate, tr.bdate, tr.type, tr.category, tr.card, tr.commission,
                    tr.gross_amount, tr.original_amount, tr.original_currency, tr.country, tr.original_commission,
                    tr.original_commission_currency, tr.original_gross_amount, tr.investments, tr.raw
                    )
                trs.append(tr)

            x += 1
            actions = ActionChains(self.driver)
            actions.send_keys(Keys.SPACE).perform()
            actions.send_keys(Keys.SPACE).perform()
            try:
                self.driver.find_element_by_xpath('//div[@class="loader"]')
                self.browser.wait_xpath_invisible('//div[@class="loader"]')
            except NoSuchElementException:
                pass

        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '.')
        return Decimal('0') if stringy == '' else Decimal(stringy)