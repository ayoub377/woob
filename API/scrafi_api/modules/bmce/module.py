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
from dateutil.relativedelta import relativedelta

from woob.tools.backend import Module, BackendConfig
from woob.tools.value import ValueBackendPassword
from woob.capabilities.bank import CapBank
from woob.scrafi_exceptions import DateLimitError

from .browser import BMCEBrowser


__all__ = ['BMCEModule']


class BMCEModule(Module, CapBank):
    NAME = 'bmce'
    DESCRIPTION = 'BMCE Bank entreprise'
    MAINTAINER = 'Zhor Abid'
    EMAIL = 'zhor.abid@gmail.com'
    LICENSE = 'LGPLv3+'
    VERSION = '3.1'

    BROWSER = BMCEBrowser

    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Identifiant', masked=False),
        ValueBackendPassword('password', label='Mot de passe', masked=True)
    )

    def create_default_browser(self):
        return self.create_browser(self.config)


    def iter_accounts(self):
        return self.browser.get_accounts()


    def get_account(self, id_):
        return self.browser.get_account(id_)
            

    def iter_history(self, _id, **kwargs):
        if datetime.strptime(kwargs['start_date'], "%d/%m/%Y") < datetime.today() - relativedelta(months=6):
            kwargs['start_date'] = (datetime.today() - relativedelta(months=6)).strftime("%d/%m/%Y")
        return self.browser.iter_history(_id, **kwargs)