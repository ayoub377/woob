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


import time, hashlib, requests, base64
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException

from woob.browser.selenium import SeleniumPage, VisibleXPath

from woob.capabilities.profile import Person
from woob.capabilities.bill import Bill, Subscription
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


class ImpayePage(SeleniumPage):
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

    def get_impaye(self):
        impayes = []
        lines = self.driver.find_elements_by_xpath('//table[@id="thetable"]/tbody/tr')
        for line in lines:
            n_police = line.find_element_by_xpath('.//td[3]').text.rstrip()

            impaye = LydecBill()
            impaye.facture = line.find_element_by_xpath('.//td[1]').text
            impaye.sub_id = n_police
            impaye.duedate = datetime.strptime(line.find_element_by_xpath('.//td[5]').text, '%d/%m/%Y').date()
            impaye.total_price = line.find_element_by_xpath('.//td[7]/a').text
            impaye.currency = 'MAD'
            
            str_2_hash = impaye.facture + impaye.duedate.strftime('%d/%m/%Y') + str(impaye.total_price)
            impaye.id = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

            del (
                impaye.vat, impaye.pre_tax_price, impaye.startdate, impaye.finishdate, impaye.date,
                impaye.format, impaye.label, impaye.type, impaye.transactions, impaye.number
            )
            impayes.append(impaye)
        return impayes
        

class LydecBill(Bill):
    montant = StringField('Montant de la facture')
    date = StringField('Date de la facture')
    tva = StringField('TVA de la facture')
    url = StringField('URL de la facture')
    
    def __repr__(self):
        return '<%s number=%r date=%r montant=%r tva=%r pdf=%r>' % (
            type(self).__name__, self.number, self.date, self.montant, self.tva, self.pdf)


class BillsPage(SeleniumPage):
    is_here = VisibleXPath('//h1[contains(text(),"Mes factures")]')

    def get_bills(self, date):
        the_date = datetime.strptime(date, "%d/%m/%Y")
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
                bill.number = tr.find_element_by_xpath('./td[1]').text.rstrip()

                prd_fact = tr.find_element_by_xpath('./td[2]').text.rstrip()
                bill.date = datetime.strptime(prd_fact, "%Y%m").strftime("%m/%Y")

                bill.montant = tr.find_element_by_xpath('./td[3]').text
                bill.tva = tr.find_element_by_xpath('./td[4]').text
                url = tr.find_element_by_xpath('./td[7]/a').get_attribute("href")

                pdf = requests.get(url, verify=False)
                bill.pdf = base64.urlsafe_b64encode(pdf.content).decode('utf8')
                                
                str_2_hash = bill.number + bill.date + bill.montant
                bill.hashid = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

                bills.append(bill)
        return bills