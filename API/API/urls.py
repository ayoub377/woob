"""API URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from scrafi_api import views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('o/', include('oauth2_provider.urls', namespace='oauth2_provider')), 

    path('bank/bankHistory/Synchro/<bank>', views.HistorySynchro.as_view(), name='HistorySynchro'),
    path('bank/bankHistory/Create/<bank>', views.HistoryCreate.as_view(), name='HistoryCreate'),

    path('bank/Synchro/<bank>', views.HistorySynchro.as_view(), name='HistorySynchro'),
    path('bank/Create/<bank>', views.HistoryCreate.as_view(), name='HistoryCreate'),

    path('bill/Synchro/<bill>', views.BillSynchro.as_view(), name='BillSynchro'),
    path('bill/Create/<bill>', views.BillCreate.as_view(), name='BillCreate'),

    path('bankHistory/getResult', views.Results.as_view(), name='Results'),
    path('bankHistory/Confirmation', views.Confirmation.as_view(), name='Confirmation'),

    path('billHistory/getResult', views.Results.as_view(), name='Results'),
    path('billHistory/Confirmation', views.Confirmation.as_view(), name='Confirmation'),

    path('getResult', views.Results.as_view(), name='Results'),
    path('Confirmation', views.Confirmation.as_view(), name='Confirmation'),

    re_path(r'.*', views.other_paths, name='OtherPaths')

]
