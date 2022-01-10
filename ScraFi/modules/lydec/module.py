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


from woob.tools.backend import Module, BackendConfig
from woob.tools.value import ValueBackendPassword

from woob.capabilities.base import NotAvailable, find_object
from woob.capabilities.profile import CapProfile
from woob.capabilities.bill import (
    CapDocument, Subscription, SubscriptionNotFound,
    Document, DocumentNotFound, DocumentTypes,
)

from .browser import LydecBrowser


__all__ = ['LydecModule']


class LydecModule(Module, CapDocument, CapProfile):
    NAME = 'lydec'
    DESCRIPTION = 'Lyonnaise des Eaux de Casablanca'
    MAINTAINER = 'Zhor Abid'
    EMAIL = 'zhor.abid@gmail.com'
    LICENSE = 'LGPLv3+'
    VERSION = '3.1'

    BROWSER = LydecBrowser

    CONFIG = BackendConfig(
        ValueBackendPassword('login', label='Utilisateur', masked=False),
        ValueBackendPassword('password', label='Mot de passe', masked=True)
    )

    accepted_document_types = (DocumentTypes.BILL, DocumentTypes.CONTRACT, DocumentTypes.OTHER)

    def create_default_browser(self):
        print('create_default_browser')
        return self.create_browser(self.config)

    def connect(self):
        print('connect')
        return self.browser.connect()

    def get_profile(self):
        print('get_profile')
        return self.browser.get_profile()

    def iter_subscription(self):
        print('iter_subscription')
        return self.browser.iter_subscriptions()
    
    def get_subscription(self, _id):
        print('get_subscription')
        return find_object(self.iter_subscription(), id=_id, error=SubscriptionNotFound)

    def get_bills(self):
        print('get_bills')
        return self.browser.get_bills()
    
    def iter_bills(self, sub_id):
        print('iter_bills')
        for bill in self.get_bills():
            if bill.sub_id == sub_id:
                return bill
        
    def iter_documents(self, sub_id):
        print('iter_documents')
        return self.browser.iter_documents(sub_id)
            
    def get_document(self, _id):
        print('get_document')
        return find_object(self.iter_documents(), id=_id, error=DocumentNotFound)

    def download_document(self, document):
        print('download_document')
        if not isinstance(document, Document):
            document = self.get_document(document)
        if document.url is NotAvailable:
            return
        return self.browser.open(document.url).content
    
    def get_details(self, sub_id):
        print('get_details')
        if sub_id == '':
            for sub in self.browser.iter_subscriptions():
                yield self.browser.get_details(sub)
        else:
            sub = self.get_subscription(sub_id)
            return self.browser.get_details(sub)

    def iter_resources(self, objs, split_path):
        print('iter_resources')
        if Subscription in objs:
            self._restrict_level(split_path)
            return self.iter_subscription()