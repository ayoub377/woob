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


import hashlib
from decimal import Decimal

from woob.browser.elements import ItemElement, TableElement, method
from woob.browser.filters.standard import CleanDecimal, CleanText, Date, Field, Format
from woob.browser.filters.html import CleanHTML, TableCell
from woob.browser.pages import FormNotFound, HTMLPage, LoggedPage

from woob.capabilities.bank.base import Account, Transaction
from woob.capabilities.base import DecimalField, StringField
from woob.scrafi_exceptions import NoHistoryError
from woob.tools.date import parse_french_date


def get_titrePage(self):
    self.titrePage = CleanHTML('//div[@class="titrePage"]')
    return self.titrePage


class LoginPage(HTMLPage):
    def login(self, username, password):
        form = self.get_form(name='identif')
        form['Contrat'] = username
        form['Password'] = password
        form['id'] = '0'
        form.submit()
        
    def form_is_here(self):
        try:
            self.get_form(name='identif')
            return True
        except FormNotFound:
            return False
            

class HomePage(LoggedPage, HTMLPage):
    def is_logged(self):
        if self.doc.xpath('//div[@id="table_infos_client"]'):
            return True


class ControlPage(HTMLPage):
    pass


class SynthesePage(LoggedPage, HTMLPage):
    def get_accounts(self):
        accounts = []
        elements = self.doc.xpath('//td/div/a/b/font/../../../..')
        for element in elements:
            account = Account()
            account.id = element.getparent().xpath('.//div/a/b/font')[0].text.split(' ')[1]
            account.label = element.getparent().xpath('.//div/@title')[0].split('Libellé	: ')[1]
            account.url = 'https://banquepopulaireentreprise.gbp.ma/Compte/' + element.getparent().xpath('.//div/a/@href')[0]
            accounts.append(account)
        return accounts

        
class HistoryPage(LoggedPage, HTMLPage):
    def get_history(self, account, **kwargs):
        form = self.get_form(name='form1')
        form['cpt'] = account.id
        form['DateOperD'] = kwargs['start_date']
        form['DateOperF'] = kwargs['end_date']
        form.submit()


class ChaabiTransaction(Transaction):
    solde = DecimalField('Le solde de la transaction')
    hashid = StringField('Scrafi ID')

    def __repr__(self):
        return '<%s hashid=%r date=%r label=%r solde=%r>' % (
            type(self).__name__, self.hashid, self.date, self.label, self.solde)
            

hashids = []
class HistoryReponse(HTMLPage, LoggedPage):
    def verify(self):
        if self.doc.xpath('//td[text()="Aucune opération ne correspond aux critères choisis."]'):
            self.browser.error_msg = 'nohistory'
            raise NoHistoryError

    @method
    class iter_table(TableElement):
        head_xpath = '//table[@id="releve"]/tr/th'

        col_label = 'Libellé' 
        col_date = 'Date OPE'
        col_debit = 'Débit'
        col_credit = 'Crédit'

        item_xpath = '//table[@id="releve"]/tr[position() > 3 and @align="center"]'
        class item(ItemElement):
            klass = ChaabiTransaction
            
            obj_label = CleanText(TableCell('label'), replace=[["\u2019", "\'"]])
            obj_date = Date(CleanText(TableCell('date')), parse_func=parse_french_date)
            
            def obj_solde(self):
                debit = CleanDecimal.French(TableCell('debit'), default=Decimal('0'))(self)
                credit = CleanDecimal.French(TableCell('credit'), default=Decimal('0'))(self)
                solde = credit - debit
                return solde
            
            obj_amount = obj_solde
            
            def obj_hashid(self):
                str_2_hash = Format('%s %s %s', Field('label'), Field('date'), Field('solde'))(self)
                hashid = hashlib.md5(str_2_hash.encode("utf-8")).hexdigest()

                x = 1
                while hashid in hashids:
                    str_to_hash = str_2_hash + str(x)
                    hashid = hashlib.md5(str_to_hash.encode("utf-8")).hexdigest()
                    x += 1

                hashids.append(hashid)
                return hashid