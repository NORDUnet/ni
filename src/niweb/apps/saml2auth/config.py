import saml2
from os import path
from os import environ
from saml2.saml import NAMEID_FORMAT_EMAILADDRESS  # noqa

BASEDIR = path.dirname(path.abspath(__file__))
# HOSTNAME = environ.get('HOSTNAME', 'localhost:8000')
HOSTNAME = 'localhost:8000'

SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': f"https://{HOSTNAME}/saml2/metadata/",

    # directory with attribute mapping
    'attribute_map_dir': path.join(BASEDIR, 'attribute-maps/'),

    # this block states what services we provide
    'service': {
    # we are just a lonely SP
        'sp' : {
            'name': f"https://{HOSTNAME}/saml2/metadata/",
            'endpoints': {
                # url and binding to the assetion consumer service view
                # do not change the binding or service name
                'assertion_consumer_service': [
                    (f"https://{HOSTNAME}/saml2/acs/", saml2.BINDING_HTTP_POST),
                ],
                # url and binding to the single logout service view
                # do not change the binding or service name
                'single_logout_service': [
                    (f"https://{HOSTNAME}/saml2/ls/", saml2.BINDING_HTTP_REDIRECT),
                    (f"https://{HOSTNAME}/saml2/ls/post/", saml2.BINDING_HTTP_POST),
                ],
            },

            # attributes that this project need to identify a user
            'required_attributes': ['eduPersonPrincipalName', 'displayName'],
            'name_id_format': [NAMEID_FORMAT_EMAILADDRESS],
            'authn_requests_signed': True,
            'want_response_signed': True,
            'want_assertions_signed': True,
            'allow_unsolicited': True,
        },
    },
    # where the remote metadata is stored
    'metadata': {
        #'local': [path.join(BASEDIR, 'remote_metadata.xml')],
        'mdq': [
            # {
            #     "url": "https://mds.swamid.se",
            #     "cert": path.join(BASEDIR, "md-signer2.crt"),
            # }
            {
                "url": "https://mds.swamid.se/qa/",
                "cert": path.join(BASEDIR, "swamid-qa.crt"),
            }
        ]
    },
    # set to 1 to output debugging information
    'debug': 1,
    # certificate
    'key_file': path.join(BASEDIR, 'certificates/private.key'),  # private part
    'cert_file': path.join(BASEDIR, 'certificates/public.cert'),  # public part
    # Encryption
    # with: openssl req -nodes -new -x509 -days 3650 -keyout private.key -out public.cert -subj '/CN=sp.localhost.com'
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

