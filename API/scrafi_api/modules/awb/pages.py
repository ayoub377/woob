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
import time

from woob.capabilities.base import DecimalField
from woob.capabilities.bank.base import Account, Transaction

from woob.browser.selenium import SeleniumPage, VisibleXPath
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from woob.scrafi_exceptions import NoHistoryError, WebsiteError, WrongCredentialsError


class HomePage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="root"]/div/div/div[1]/div/div[1]/button')

    def go_login_page(self):
        self.driver.find_element(By.XPATH, '//*[@id="root"]/div/div/div[1]/div/div[1]/button').click()


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="username"]')
    
    def login(self, username, password):
        self.driver.find_element(By.XPATH, '//*[@id="username"]').send_keys(username)
        self.driver.find_element(By.XPATH, '//*[@id="password"]').send_keys(password)
        self.driver.find_element(By.XPATH, '//*[@id="kc-form-buttons"]').click()
        
        
class ErrorPage(SeleniumPage):
    def check_error(self):
        try:
            self.driver.find_element(By.XPATH, '//div[@class="alert alert-error"]')
            self.browser.error_msg = 'credentials'
            raise WrongCredentialsError
        except NoSuchElementException:
            self.browser.error_msg = 'bank'
            raise WebsiteError


class DashboardPage(SeleniumPage):
    pass


class AccountsPage(SeleniumPage):
    is_here = VisibleXPath('/html/body/div[1]/div/main/div/div/div[2]/div/div[1]/div/span')

    def get_accounts(self):
        accounts = []
        elements = self.driver.find_elements(By.XPATH, '//div[contains(@class, "ui-list-box")]')
        for element in elements:
            account = Account()
            time.sleep(5)
            text = element.find_element(By.XPATH, './div/div[2]/div/span[2]').text
            devise = element.find_element(By.XPATH, './div/div[3]/div/button/span/div/span[1]').text.rsplit(' ', 1)[1]
            account.id = text[-16:]
            account.label = text[:-16] + "(" + devise + ")"
            accounts.append(account)
        return accounts

    def go_history_page(self, acc_id):
        accounts = self.driver.find_elements(By.XPATH, '//div[contains(@class, "ui-list-box")]')
        for account in accounts:
            account_id = account.find_element(By.XPATH, './div/div[2]/div/span[2]').text[-16:]
            if acc_id == account_id:
                account.find_element(By.XPATH, './div/div[3]/div/button').click()
                break

class AwbTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')

    def __repr__(self):
        return '<%s id=%r date=%r label=%r solde=%r>' % (
            type(self).__name__, self.id, self.date, self.label, self.solde)

class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('//h2[contains(text(), "opérations comptabilisées")]')

    def get_history(self, **kwargs):
        start = kwargs['start_date']
        end = kwargs['end_date']
        if start != 'all':
            time.sleep(2)
            self.driver.find_element(By.XPATH, '//button[contains(@class, "ui-button contained primary")]').click()
            self.driver.find_element(By.XPATH, '//input[contains(@class, "input-is-regular")]/..').click()
            french_months = {'01': 'Janvier',
                            '02': 'Février',
                            '03': 'Mars',
                            '04': 'Avril',
                            '05': 'Mai',
                            '06': 'Juin',
                            '07': 'Juillet',
                            '08': 'Août',
                            '09': 'Septembre',
                            '10': 'Octobre',
                            '11': 'Novembre',
                            '12': 'Décembre'}
            
            check_next = True
            checker = "start"
            checker_m_y = french_months[start[3:5]] + ' ' + start[-4:]
            checker_day = int(start[:2])

            while check_next:
                months = self.driver.find_elements(By.XPATH, '//div[@class="DayPicker-Months"]/div')

                for month in months:
                    month_name = month.find_element(By.XPATH, './/div[1]/div').text

                    if month_name == checker_m_y:
                        days = month.find_elements(By.XPATH, './/div[3]/div/div')
                        for day in days:
                            if day.text == '':
                                continue
                            day_number = int(day.text)
                            
                            if day_number == checker_day:
                                day.click()
                                if checker == "start":
                                    checker = "end"
                                    checker_m_y = french_months[end[3:5]] + ' ' + end[-4:]
                                    checker_day = int(end[:2])
                                    if month_name == checker_m_y:
                                        if day_number == checker_day:
                                            day.click()
                                            check_next = False
                                            break
                                        else:
                                            continue
                                    else:
                                        break
                                else:
                                    check_next = False
                                    break

                    if not check_next:
                        break

                if check_next and checker == "start":
                    self.driver.find_element(By.XPATH, '//span[@aria-label="Previous Month"]').click()

                if check_next and checker == "end":
                    self.driver.find_element(By.XPATH, '//span[@aria-label="Next Month"]').click()
                    
            time.sleep(1)
            self.driver.find_element(By.XPATH, '//span[text()="Confirmer"]').click()

        trs = []
        ids = []
        try:
            self.driver.find_element(By.XPATH, '//span[contains(text(), "Opération introuvable")]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except NoSuchElementException:
            pass
        
        time.sleep(1)
        self.driver.find_element(By.XPATH, '//button[contains(@class, "ui-button-dropdown-number")]').click()
        self.driver.find_element(By.XPATH, '//li[contains(text(),"100")]').click()

        pages = self.driver.find_elements(By.XPATH, '//ul[@class="pagination"]/li')
        pages = pages[1:-1]

        for page in pages:
            lines = self.driver.find_elements(By.XPATH, '//div[contains(@class, "ui-list-box")]')

            for line in lines:
                if line.find_element(By.XPATH, './/div/div[1]/span').text != 'Total':
                    tr = AwbTransaction()
                    
                    tr.label = line.find_element(By.XPATH, './/div/div[1]/span').text
                    tr.date = datetime.strptime(line.find_element(By.XPATH, './/div/div[2]/span').text, '%d/%m/%Y').date()

                    debit = self.decimalism(line.find_element(By.XPATH, './/div/div[4]/div').text)
                    credit = self.decimalism(line.find_element(By.XPATH, './/div/div[5]/div').text)
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

            self.driver.find_element(By.XPATH, '//ul[@class="pagination"]/li[last()]').click()
        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '.')
        stringy = stringy.replace('+', '').replace('-', '')
        if stringy == '-' or stringy == '':
            return Decimal('0')  
        else:
            return Decimal(stringy)
