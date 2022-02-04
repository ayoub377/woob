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


import csv, os

from woob.browser.browsers import LoginBrowser, need_login
from woob.capabilities.bank import Account
from woob.scrafi_exceptions import IdNotFoundError, NoHistoryError, WebsiteError, WrongCredentialsError


path = os.path.expanduser('~')
if "C:" in path:
    path = path.replace('\\', '/')

class IneoBrowser(LoginBrowser):
    error_msg = ''
    logged = False
    
    def do_login(self):
        # self.error_msg = 'bank'
        # raise WebsiteError
        if self.username == 'ineologin' and self.password == 'ineopass':
            self.logged = True
        else:
            self.error_msg = 'credentials'
            raise WrongCredentialsError

    @need_login
    def get_accounts(self):
        lista = []
        
        a = Account()
        a.id = '123'
        a.label = 'Compte courant'
        lista.append(a)
        
        b = Account()
        b.id = '456'
        b.label = 'Compte épargne'
        lista.append(b)
        
        c = Account()
        c.id = '789'
        c.label = 'Compte sur carnet'
        lista.append(c)

        return lista

    @need_login
    def get_account(self, id_):
        for account in self.get_accounts():
            if account.id == id_:
                return account
        self.error_msg = 'ID'
        raise IdNotFoundError

    @need_login
    def iter_history(self, id_, **kwargs):
        self.get_account(id_)
        start_date = kwargs['start_date']
        end_date = kwargs['end_date']

        if start_date == '10/10/2021' or end_date == '11/11/2021':
            self.error_msg = 'nohistory'
            raise NoHistoryError

        with open(path + '/scrafi_project/ineo_response.csv', 'r') as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader)
            dico = [dict(zip(headers, i)) for i in reader]
        return dico