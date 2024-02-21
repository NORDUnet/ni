import configparser
import sys


def get_authorized_users(filename, allowed_groups = ['*']):
    def get_auth_users(groups, allowed_groups):
        auth_users = []
        groups_keys = list(groups.keys())
        for key in groups_keys:
            if key in allowed_groups:
                auth_users.extend(groups[key].split(','))
            elif '*' in allowed_groups:
                auth_users.extend(groups[key].split(','))
        return [x.strip() for x in auth_users]
    
    def get_users_from_identifiers(staffs, groups, allowed_groups):
        groups_keys = list(groups.keys())
        if not isinstance(staffs, str):
            return staffs
        
        if staffs == '*':
            staffs = ', '.join(auth_users)
        else:
            for key in groups_keys:
                if key in allowed_groups:
                    staffs = staffs.replace(str(key), groups[key])
                elif '*' in allowed_groups:
                    staffs = staffs.replace(str(key), groups[key])
        return staffs
    
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
    staff_users = get_users_from_identifiers(staffs, groups, allowed_groups)
    superusers = get_users_from_identifiers(superusers, groups, allowed_groups)
    auth_data =  get_auth_data_dict(auth_users, staff_users, superusers)
    return auth_data
    

