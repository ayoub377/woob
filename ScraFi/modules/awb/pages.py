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
from woob.scrafi_exceptions import NoHistoryError, WebsiteError, WrongCredentialsError


class HomePage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="root"]/div/div/div[1]/div/button')

    def go_login_page(self):
        self.driver.find_element_by_xpath('//*[@id="root"]/div/div/div[1]/div/button').click()


class LoginPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="username"]')
    
    def login(self, username, password):
        self.driver.find_element_by_xpath('//*[@id="username"]').send_keys(username)
        self.driver.find_element_by_xpath('//*[@id="password"]').send_keys(password)
        self.driver.find_element_by_xpath('//*[@id="kc-form-buttons"]/button').click()
        
        
class ErrorPage(SeleniumPage):
    def check_error(self):
        try:
            self.driver.find_element_by_xpath('//div[@class="alert alert-error"]')
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
        account = Account()
        text = self.driver.find_element_by_xpath('//div[@class="sc-AykKD MTDcI"]/span[2]').text
        account.id = text[-16:]
        account.label = text[:-16]
        accounts.append(account)
        return accounts

    def go_history_page(self):
        self.driver.find_element_by_xpath('//*[@id="root"]/div/main/div/div/div[2]/div/div[3]/div/div/div[4]/button').click()


class AwbTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')


class HistoryPage(SeleniumPage):
    is_here = VisibleXPath('/html/body/div[1]/div/main/div/div/div[2]/div/div[1]/div/h2')

    def get_history(self, **kwargs):
        start = kwargs['start_date']
        end = kwargs['end_date']

        self.driver.find_element_by_xpath('//button[@class="sc-AykKC fqejMj ui-button contained primary"]').click()
        self.driver.find_element_by_xpath('//div[@class="sc-AykKD kBBJUZ"]/div').click()
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
        checker = start
        checker_m_y = french_months[start[3:5]] + ' ' + start[-4:]
        checker_day = int(start[:2])

        for i in range(3):
            months = self.driver.find_elements_by_xpath('//div[@class="DayPicker-Months"]/div')

            for month in months:
                month_name = month.find_element_by_xpath('.//div[1]/div').text

                if month_name == checker_m_y:
                    days = month.find_elements_by_xpath('.//div[3]/div/div')
                    for day in days:
                        if day.text == '':
                            continue
                        day_number = int(day.text)
                        
                        if day_number == checker_day:
                            day.click()
                            if checker == start:
                                checker = end
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

            if check_next and checker == start:
                self.driver.find_element_by_xpath('//span[@aria-label="Previous Month"]').click()

            if check_next and checker == end:
                self.driver.find_element_by_xpath('//span[@aria-label="Next Month"]').click()

        self.driver.find_element_by_xpath('//span[text()="Confirmer"]').click()

        trs = []
        try:
            self.driver.find_element_by_xpath('//span[contains(text(), "Opération introuvable")]')
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError
        except NoSuchElementException:
            pass
        
        time.sleep(1)
        self.driver.find_element_by_xpath('//button[@class="sc-AykKC fqejMj ui-button ui-button-empty primary ui-button-dropdown-number"]').click()
        self.driver.find_element_by_xpath('//li[contains(text(),"100")]').click()

        pages = self.driver.find_elements_by_xpath('//ul[@class="pagination"]/li')
        pages = pages[1:-1]

        for page in pages:
            lines = self.driver.find_elements_by_xpath('//div[@class="sc-AykKD jEjZCD sc-fzXfNM gaplSw ui-list-box"]')

            for line in lines:
                if line.find_element_by_xpath('.//div/div[1]/span').text != 'Total':
                    tr = AwbTransaction()
                    
                    tr.label = line.find_element_by_xpath('.//div/div[1]/span').text
                    tr.date = datetime.strptime(line.find_element_by_xpath('.//div/div[2]/span').text, '%d/%m/%Y').date()

                    debit = self.decimalism(line.find_element_by_xpath('.//div/div[4]/div').text)
                    credit = self.decimalism(line.find_element_by_xpath('.//div/div[5]/div').text)
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

            page.click()
        return trs
                    
    def decimalism(self, stringy):
        stringy = stringy.replace(' ', '').replace(',', '.')
        stringy = stringy.replace('+', '').replace('-', '')
        if stringy == '-' or stringy == '':
            return Decimal('0')  
        else:
            return Decimal(stringy)
