from os import environ, path
import saml2
from saml2.saml import NAMEID_FORMAT_EMAILADDRESS  # noqa

SERVER_NAME =  environ.get("SERVER_NAME", "norpan-ni.cnaas.sunet.se")

BASEDIR = path.dirname(path.abspath(__file__))
SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': f"https://{SERVER_NAME}/saml2/metadata/",

    # directory with attribute mapping
    'attribute_map_dir': path.join(BASEDIR, 'attribute-maps/'),

    # this block states what services we provide
    'service': {
        'sp': {
            'name': f"https://{SERVER_NAME}/saml2/metadata/",
            'endpoints': {
                'assertion_consumer_service': [
                    (f"https://{SERVER_NAME}/saml2/acs/", saml2.BINDING_HTTP_POST),
                ],
                'single_logout_service': [
                    (f"https://{SERVER_NAME}/saml2/ls/", saml2.BINDING_HTTP_REDIRECT),
                    (f"https://{SERVER_NAME}/saml2/ls/post/", saml2.BINDING_HTTP_POST),
                ],
            },
            'name_id_format': [NAMEID_FORMAT_EMAILADDRESS],
            'authn_requests_signed': True,
            'want_response_signed': True,
            'want_assertions_signed': True,
            'allow_unsolicited': True,
            'idp': {
                # we do not need a WAYF service since there is
                # only an IdP defined here. This IdP should be
                # present in our metadata
                # the keys of this dictionary are entity ids
                #'https://idp-test.nordu.net/idp/shibboleth': None,
                'https://shared-sso-proxy1.cnaas.sunet.se/idp': None,
            },
        },
    },
    # where the remote metadata is stored
    'metadata': {
        'local': [path.join(BASEDIR, '/opt/sso/shibboleth/frontend.xml')], # frontend.xml
        # 'mdq': [
        #     {"url": "https://mds.swamid.se",
        #         "cert": path.join(BASEDIR, "certificates/md-signer2.crt"),
        #     }
        # ]
    },
    # set to 1 to output debugging information
    'debug': 1,
    # certificate
    # 'key_file': path.join(BASEDIR, 'certificates/private.key'),  # private part
    'key_file': '/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/privkey.pem',  # private part
    'cert_file': '/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/cert.pem',  # public part
    # Encryption
    'encryption_keypairs': [{
        'key_file': '/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/privkey.pem',
        'cert_file': '/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/cert.pem',
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

