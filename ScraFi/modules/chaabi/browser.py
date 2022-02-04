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


from woob.browser import URL
from woob.browser.browsers import LoginBrowser, need_login
from woob.scrafi_exceptions import IdNotFoundError, WebsiteError, WrongCredentialsError

from .pages import LoginPage, HomePage, ControlPage, SynthesePage, HistoryPage, HistoryReponse


class ChaabiBrowser(LoginBrowser):
    BASEURL = 'https://banquepopulaireentreprise.gbp.ma'

    login_page = URL(r'/accueil/accueil.asp', LoginPage)
    home_page = URL(r'/compte/index2.asp', HomePage)
    control_page = URL(r'/identification/controle.asp', ControlPage)
    synth_page = URL(r'/Compte/Syn_Cpt.asp', SynthesePage)
    history_page = URL(r'/Compte/His_Cpt_Req.asp', HistoryPage)
    history_rep_page = URL(r'/Compte/His_Cpt_Rep.asp', HistoryReponse)

    logged = False
    error_msg = ''
    
    def do_login(self):
        self.login_page.go()
        if self.login_page.is_here():
            self.page.login(self.username, self.password)
            self.login_page.go()
            if self.page.form_is_here():
                self.error_msg = 'credentials'
                raise WrongCredentialsError
            else:
                self.logged = True
                self.home_page.go()
        else:
            self.error_msg = 'bank'
            raise WebsiteError

    @need_login
    def get_accounts(self):
        self.synth_page.go()
        return self.page.get_accounts()

    @need_login
    def get_account(self, id_):
        for account in self.get_accounts():
            if account.id == id_:
                return account
        self.error_msg = 'ID'
        raise IdNotFoundError
    
    @need_login
    def iter_history(self, id_, **kwargs):
        account = self.get_account(id_)
        self.history_page.stay_or_go()
        self.page.get_history(account, **kwargs)
        history = []
        self.page.verify()
        for i in self.page.iter_table():
            del (
                i.investments, i.url, i.rdate, i.vdate, i.bdate, i.type, i.raw, i.category,
                i.card, i.commission, i.gross_amount, i.original_amount, i.original_currency,
                i.country, i.original_commission, i.original_commission_currency, i.original_gross_amount
            )
            history.append(i)
        return history