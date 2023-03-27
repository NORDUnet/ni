import utils
import argparse
import logging
from apps.noclook import helpers, forms
from apps.noclook.models import ServiceType, NodeHandle

logger = logging.getLogger('noclook_bulk_service')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--servicetype', '-s', help='Service type e.g. EVPN')
    parser.add_argument('--nbr', '-n', type=int, help='Amount of services to create')
    parser.add_argument('--provider', default='NORDUnet', help='Service provider defaults to NORDUnet')
    parser.add_argument('--verbose', '-V', action='store_true', default=False)
    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.INFO)

    # check that service type exists
    stype = ServiceType.objects.get(name__iexact=args.servicetype)
    provider = NodeHandle.objects.get(node_name__iexact=args.provider, node_type__slug='provider')

    user = utils.get_user()

    for i in range(args.nbr):
        form = forms.NewServiceForm({
            'service_class': stype.service_class.name,
            'service_type': stype.name,
            'operational_state': 'In service',
            'relationship_provider': provider.handle_id,
        })
        if form.is_valid():
            nh = helpers.create_unique_node_handle(user, form.cleaned_data['name'], 'service', 'Logical')
            helpers.form_update_node(user, nh.handle_id, form)
            print(nh.node_name)
        else:
            logger.error('Error validating form: %s', form.errors.items())


if __name__ == '__main__':
    logger.setLevel(logging.WARNING)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    main()
