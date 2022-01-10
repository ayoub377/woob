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
from dateutil.relativedelta import relativedelta
from selenium.common.exceptions import NoSuchElementException

from woob.browser.selenium import SeleniumPage, VisibleXPath

from woob.capabilities.profile import Person
from woob.capabilities.bill import Bill, Document, Subscription
from woob.capabilities.base import StringField


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
    """
    We only need this class to prevent browser from considering
    other pages as accueil page.
    """
    is_here = VisibleXPath('//span[contains(text(),"Accueil")]')


class LydecPerson(Person):
    def __repr__(self):
        return '<%s name=%r country=%r phone=%r mobile=%r email=%r>' % (
        type(self).__name__, self.name, self.country, self.phone, self.mobile, self.email
    )
        
        
class ProfilePage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="p_p_id_InfosClient_WAR_InfosClientportlet_"]')

    def get_profile(self):
        p = LydecPerson()
        p.name = self.driver.find_element_by_xpath('//*[@id="topnav"]/a').text
        p.country = self.driver.find_element_by_xpath('//*[@id="indicatif"]/option[@selected="selected"]').text
        p.phone = self.driver.find_element_by_xpath('//*[@id="fixe"]').get_attribute('value')
        p.mobile = self.driver.find_element_by_xpath('//*[@id="gsm"]').get_attribute('value')
        p.email = self.driver.find_element_by_xpath('//*[@id="email"]').get_attribute('value')

        del(
            p.birth_date, p.firstname, p.lastname, p.nationality, p.gender, p.maiden_name, p.spouse_name,
            p.children, p.family_situation, p.matrimonial, p.housing_status, p.job, p.job_start_date,
            p.job_activity_area, p.job_contract_type, p.company_name, p.company_siren, p.socioprofessional_category,
            p.postal_address, p.professional_phone, p.professional_email, p.main_bank
        )
        return p


class LydecSub(Subscription):
    etat_contrat = StringField('Contract state')
    address = StringField('Address')
    conso = StringField('Consomation')
    impaye = StringField('Les impayés')


class SubscriptionPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Mes Contrats")]')

    def get_subscriptions(self):
        subs = []
        lines = self.driver.find_elements_by_xpath('//*[@id="thetable"]/tbody/tr')
        for line in lines:
            sub = LydecSub()
            sub.id = line.find_element_by_xpath('.//td[2]/a').text
            sub.label = self.set_label(line.find_element_by_xpath('.//td[1]/img').get_attribute('src'))
            sub.etat_contrat = line.find_element_by_xpath('.//td[3]').text
            sub.address = line.find_element_by_xpath('.//td[4]').text
            sub.conso = line.find_element_by_xpath('.//td[5]').text
            sub.impaye = line.find_element_by_xpath('.//td[7]/a').text

            del (sub.subscriber, sub.validity, sub.renewdate)
            subs.append(sub)
        return subs

    def set_label(self, img):
        """
        Each Lydec's contract has a type: Eau / Electricité
        The type is displayed as an image on the website.
        Converting images to their meaning
        """
        if img.endswith("1.gif"):
            return 'Eau'
        elif img.endswith("2.gif"):
            return 'Electricité'


class LydecBill(Bill):
    facture = StringField('La facture à payer')
    sub_id = StringField('The bill subscription ID')
    
    def __repr__(self):
        return '<%s facture=%r sub=%r duedate=%r total_price=%r currency=%r>' % (
        type(self).__name__, self.facture, self.sub_id, self.duedate, self.total_price, self.currency
    )


class BillsPage(SeleniumPage):
    is_here = VisibleXPath('//*[@id="p_p_id_Impayes_WAR_Impayesportlet_"]')

    def tax_details(self):
        """
        Tax details about unpaid bills are on a JavaScript rendered popup.
        After the click: get the bill details then taxes.
        """
        self.driver.find_element_by_xpath('//*[@id="thetable"]/tbody/tr[1]/td[7]/a').click()
        time.sleep(2)
        # self.logger.error('DETAILS ARE HERE')  
              
        details = self.driver.find_elements_by_xpath('//td[@class="contrat1"]')
        n_contrat = details[0].text
        n_facture = details[1].text
        montant_facture_ttc = details[2].text
        # taux_tva = 

    def get_bills(self):
        bills = []
        lines = self.driver.find_elements_by_xpath('//table[@id="thetable"]/tbody/tr')
        for line in lines:
            n_police = line.find_element_by_xpath('.//td[3]').text.rstrip()

            bill = LydecBill()
            bill.facture = line.find_element_by_xpath('.//td[1]').text
            bill.sub_id = n_police
            bill.duedate = datetime.strptime(line.find_element_by_xpath('.//td[5]').text, '%d/%m/%Y').date()
            bill.total_price = line.find_element_by_xpath('.//td[7]/a').text
            bill.currency = 'MAD'
            
            str_2_hash = bill.facture + bill.duedate.strftime('%d/%m/%Y') + str(bill.total_price)
            bill.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

            del (
                bill.vat, bill.pre_tax_price, bill.startdate, bill.finishdate, bill.date,
                bill.format, bill.label, bill.type, bill.transactions, bill.number
            )
            bills.append(bill)
        return bills
        

class LydecDoc(Document):
    prd_fact = StringField('Produit de facturation')


class DocumentsPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Mes factures")]')

    def get_documents(self, id, date):
        self.driver.find_element_by_xpath('//option[contains(@value, "%s")]' %id).click()

        month = date.strftime("%m")
        self.driver.find_element_by_xpath('//select[@name="moisD"]/option[contains(@value, "%s")]' %month).click()
        self.driver.find_element_by_xpath('//select[@name="moisF"]/option[contains(@value, "%s")]' %month).click()

        year = date.strftime("%Y")
        selected_year = self.driver.find_element_by_xpath('//select[@name="anneeD"]/option[1]').text
        if year != selected_year:
            self.driver.find_element_by_xpath('//select[@name="anneeD"]/option[contains(@value, "%s")]' %year).click()
            self.driver.find_element_by_xpath('//select[@name="anneeF"]/option[contains(@value, "%s")]' %year).click()

        self.driver.find_element_by_xpath('//*[@id="submit"]').click()
        time.sleep(2)

        doc = LydecDoc()
        doc.date = date - relativedelta(months=1)
        doc.format = 'PDF'
        doc.type = self.driver.find_element_by_xpath('//*[@id="formulaire"]/table/tbody/tr/td[2]').text
        doc.number = self.driver.find_element_by_xpath('//tr[@class="tdalt1"]/td[1]').text.rstrip()
        doc.prd_fact = self.driver.find_element_by_xpath('//tr[@class="tdalt1"]/td[2]').text.rstrip()
        doc.url = self.driver.find_element_by_xpath('//*[@id="thetable"]/tbody/tr/td[7]/a').get_attribute("href")
        
        del (doc.label, doc.transactions)
        return doc