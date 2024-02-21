import configparser
import sys


def get_authorized_users(filename, allowed_groups = ['su']):
    def get_auth_users(groups, allowed_groups):
        if not (isinstance(allowed_groups, list) or allowed_groups == '*'):
            print("Allowed groups should either be a list of group names or a string '*' for all groups")
            sys.exit(1)
        auth_users = []
        groups_keys = list(groups.keys())
        if '*' in allowed_groups:
            for key in groups_keys:
                auth_users.extend(groups[key].split(','))
        else:
            for key in allowed_groups:
                    auth_users.extend(groups[key].split(','))
        return [x.strip() for x in auth_users]
    
    def get_index(data,key):
        index = None
        try:
            index =  data.index(key)
        except:  # noqa: E722
            return None
        return index
    
    def get_users_from_identifiers(group_identifiers, auth_users, groups, allowed_groups):
        if not isinstance(group_identifiers, str):
            return group_identifiers
        if not (isinstance(allowed_groups, list) or allowed_groups == '*'):
            return group_identifiers
        
        groups_keys = list(groups.keys())
        if group_identifiers == '*':
            group_identifiers = ', '.join(auth_users)
        else:
            group_identifiers = [x.strip() for x in group_identifiers.split(',')]
            if '*' in allowed_groups:
                for key in groups_keys:
                    index = get_index(group_identifiers, str(key))
                    if index is not None:
                        group_identifiers[index] = groups[key]
            else:
                for key in allowed_groups:
                    index = get_index(group_identifiers, str(key))
                    if index is not None:
                        group_identifiers[index] = groups[key]

        return ', '.join(group_identifiers)
    
    def get_auth_data_dict(auth_users, staff_users, superusers):
        auth_data = {}
        for user in auth_users:
            auth_data[user] = {"is_staff": False, "is_superuser": False }
            if user in superusers:
                auth_data[user]['is_staff'] = True
                auth_data[user]['is_superuser'] = True
            elif user in staff_users:
                auth_data[user]['is_staff'] = True
        return auth_data
    
    
    def check_config_file(filename):
        configparser.SafeConfigParser
        config = configparser.ConfigParser()
        required_sections = ['GROUPS', 'GROUPS.STAFF']
        
        try:
            file = config.read(filename)
            if len(file) == 0:
                raise IOError
        except IOError:
            print('Could not find configuration file %s' % filename)
            sys.exit(1)
        except configparser.ParsingError:
            print('There was an error parsing %s' % filename)
            sys.exit(1)
        except Exception as e:
            print('There was an unknown error parsing %s: %s' % filename, e)
            sys.exit(1)
        for sect in required_sections:
            if not config.has_section(sect):
                print(f"Config file is missing required sections {required_sections}")
                sys.exit(1)
        return config
    
    config = check_config_file(filename)
    groups = config['GROUPS']
    staffs = config['GROUPS.STAFF']['identifier'] if config.has_section('GROUPS.STAFF') else []
    superusers = config['GROUPS.SUPERUSER']['identifier'] if config.has_section('GROUPS.SUPERUSER') else []
    
    auth_users = get_auth_users(groups, allowed_groups)
    staff_users = get_users_from_identifiers(staffs, auth_users, groups, allowed_groups)
    superusers = get_users_from_identifiers(superusers, auth_users, groups, allowed_groups)
    auth_data =  get_auth_data_dict(auth_users, staff_users, superusers)
    return auth_data
    

