from os import path
import saml2
from saml2.saml import NAMEID_FORMAT_EMAILADDRESS  # noqa
from saml2.sigver import get_xmlsec_binary  # noqa

BASEDIR = path.dirname(path.abspath(__file__))
SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': 'https://localhost:8000/saml2/metadata/',

    # directory with attribute mapping
    'attribute_map_dir': path.join(BASEDIR, 'attribute-maps/'),

    # this block states what services we provide
    'service': {
        'sp': {
            'name': 'https://localhost:8000/saml2/metadata/',
            'endpoints': {
                'assertion_consumer_service': [
                    ('https://localhost:8000/saml2/acs/', saml2.BINDING_HTTP_POST),
                ],
                'single_logout_service': [
                    ('https://localhost:8000/saml2/ls/', saml2.BINDING_HTTP_REDIRECT),
                    ('https://localhost:8000/saml2/ls/post/', saml2.BINDING_HTTP_POST),
                ],
            },
            'name_id_format': [NAMEID_FORMAT_EMAILADDRESS],
            'authn_requests_signed': True,
            'want_response_signed': True,
            'want_assertions_signed': True,
            'allow_unsolicited': True,
        },
    },
    # where the remote metadata is stored
    'metadata': {
        # 'remote': [{
        #     'url': 'http://md.swamid.se/md/swamid-testing-1.0.xml',
        #     'cert': path.join(BASEDIR, 'md-signer.crt')
        # }],
        'mdq': [{"url": "https://mds.swamid.se/qa/",
                "cert": path.join(BASEDIR, "swamid-qa.crt"),
        }]
    },
    
    # 'mdq': [{"url": "https://mds.swamid.se",
    #         "cert": path.join(BASEDIR, "md-signer2.crt"),
    # }]
    # "cert": path.join(BASEDIR, "md-signer2.crt"),
    # set to 1 to output debugging information
    'debug': 1,
    # certificate
    'key_file': path.join(BASEDIR, 'certificates/private.key'),  # private part
    'cert_file': path.join(BASEDIR, 'certificates/public.cert'),  # public part
    # Encryption
    'encryption_keypairs': [{
        'key_file': BASEDIR + '/certificates/private.key',
        'cert_file': BASEDIR + '/certificates/public.cert',
    }],
    # own metadata settings
    'contact_person': [
        {'given_name': '',
         'sur_name': '',
         'company': '',
         'email_address': '',
         'contact_type': 'technical'},
    ],
    #'valid_for': 24,  # DO NOT USE
}

