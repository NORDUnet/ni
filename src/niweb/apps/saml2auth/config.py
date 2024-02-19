from os import environ, path
import saml2
from saml2.saml import NAMEID_FORMAT_EMAILADDRESS  # noqa


APP_SERVER_NAME =  environ.get("APP_SERVER_NAME", "norpan-ni.cnaas.sunet.se")
KEY_FILE =  environ.get("KEY_FILE", "/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/privkey.pem")
CERT_FILE =  environ.get("CERT_FILE", "/etc/letsencrypt/live/norpan-ni.cnaas.sunet.se/cert.pem")
SP_IDP =  environ.get("SP_IDP", None)
LOCAL_METADATA =  environ.get("LOCAL_METADATA", None)
MDQ_URL= environ.get("MDQ_URL", None)
MDQ_CERT= environ.get("MDQ_CERT", None)

BASEDIR = path.dirname(path.abspath(__file__))
SERVICE_PROVIDER = {
    'name': f"https://{APP_SERVER_NAME}/saml2/metadata/",
    'endpoints': {
        'assertion_consumer_service': [
            (f"https://{APP_SERVER_NAME}/saml2/acs/", saml2.BINDING_HTTP_POST),
        ],
        'single_logout_service': [
            (f"https://{APP_SERVER_NAME}/saml2/ls/", saml2.BINDING_HTTP_REDIRECT),
            (f"https://{APP_SERVER_NAME}/saml2/ls/post/", saml2.BINDING_HTTP_POST),
        ],
    },
    'name_id_format': [NAMEID_FORMAT_EMAILADDRESS],
    'authn_requests_signed': True,
    'want_response_signed': False,
    'want_assertions_signed': False,
    'allow_unsolicited': True,
    # "want_assertions_or_response_signed": True,
}

# we do not need a WAYF service since there is
# only an IdP defined here. This IdP should be
# present in our metadata
# the keys of this dictionary are entity ids
#'https://idp-test.nordu.net/idp/shibboleth': None,
if SP_IDP is not None:
    SERVICE_PROVIDER['idp'] = {
        SP_IDP: None,
    }
CONFIG_METADATA = None  
if LOCAL_METADATA is not None:
    CONFIG_METADATA = {
        'local': [LOCAL_METADATA],
    }
elif MDQ_URL is not None and MDQ_CERT is not None:
    CONFIG_METADATA = {
        'mdq': [
            {
                "url": MDQ_URL, 
                "cert": MDQ_CERT
            }
        ]
    }
else:
    CONFIG_METADATA = {
        'local': [path.join(BASEDIR, '/opt/sso/shibboleth/frontend.xml')],
    }

CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': f"https://{APP_SERVER_NAME}/saml2/metadata/",

    # directory with attribute mapping
    'attribute_map_dir': path.join(BASEDIR, 'attribute-maps/'),

    # this block states what services we provide
    'service': {
        'sp': SERVICE_PROVIDER,
    },
    # where the remote metadata is stored
    'metadata': CONFIG_METADATA,
    # set to 1 to output debugging information
    'debug': 1,
    # certificate
    'key_file': KEY_FILE,  # private part
    'cert_file': CERT_FILE,  # public part
    # Encryption
    'encryption_keypairs': [{
        'key_file': KEY_FILE,
        'cert_file': CERT_FILE,
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

