from os import path
import saml2
BASEDIR = path.dirname(path.abspath(__file__))
SAML_CONFIG = {
    # full path to the xmlsec1 binary programm
    'xmlsec_binary': '/usr/bin/xmlsec1',

    # your entity id, usually your subdomain plus the url to the metadata view
    'entityid': 'https://hostname/saml2/metadata/',

    # directory with attribute mapping
    'attribute_map_dir': path.join(BASEDIR, 'attribute-maps/'),

    # this block states what services we provide
    'service': {
    # we are just a lonely SP
        'sp' : {
            'name': 'Service Name',
            'endpoints': {
                # url and binding to the assetion consumer service view
                # do not change the binding or service name
                'assertion_consumer_service': [
                    ('https://hostname/saml2/acs/',
		    saml2.BINDING_HTTP_POST),
	        ],
                # url and binding to the single logout service view
                # do not change the binding or service name
                'single_logout_service': [
		    ('https://hostname/saml2/ls/',
		    saml2.BINDING_HTTP_REDIRECT),
	        ],
	    },

            # attributes that this project need to identify a user
            'required_attributes': ['eduPersonPrincipalName', 'displayName'],

            # attributes that may be useful to have but not required
            #'optional_attributes': ['eduPersonAffiliation'],

            # in this section the list of IdPs we talk to are defined
            'idp': {
                # we do not need a WAYF service since there is
                # only an IdP defined here. This IdP should be
                # present in our metadata
                # the keys of this dictionary are entity ids
	        'https://idp-test.nordu.net/idp/shibboleth': None, 
	        #'https://idp.nordu.net/idp/shibboleth': None, 
	    },
        },
    },
    # where the remote metadata is stored
    'metadata': {
        #'local': [path.join(BASEDIR, 'remote_metadata.xml')],
        'remote': [#{
            #'url': 'http://md.swamid.se/md/swamid-1.0.xml',
            #'cert': path.join(BASEDIR, 'saml2/md-signer.crt')
        #},
        {
            'url': 'http://md.swamid.se/md/swamid-testing-1.0.xml',
            'cert': path.join(BASEDIR, 'md-signer.crt')
        }]
    },
    # set to 1 to output debugging information
    'debug': 1,
    # certificate
    'key_file': path.join(BASEDIR, 'sp-key.pem'),  # private part
    'cert_file': path.join(BASEDIR, 'sp-cert.pem'),  # public part
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

