# -*- coding: utf-8 -*-
__author__ = 'lundberg'

import re

NETAPP_REPORT_SETTINGS = [
    # {'volumes': [re.compile('pattern')], 'service_id': '', 'contract_reference': '', 'total_storage': 0.0}
    {
        'volumes': [re.compile('cifs_uni[\d]+')],
        'service_id': 'NU-S000197',  # UNINETT ACP
        'contract_reference': u'UNINETT eCampus Drift U2020311 AA04 Adobe Connect Webmøter',
        'total_storage': 0.0
    },
    {
        'volumes': [re.compile('cifs_fun[\d]+')],
        'service_id': 'NU-S000198',  # FUNET ACP
        'contract_reference': 'CSC AA06 AdobeConnect',
        'total_storage': 0.0
    },
    {
        'volumes': [re.compile('cifs_sun[\d]+')],
        'service_id': 'NU-S000293',  # SUNET ACP
        'contract_reference': 'SUNET_AA14 Adobe Connect Service Operations',
        'total_storage': 0.0
    },
]