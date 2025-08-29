# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## [Unreleased]

## 2025-08-29
## Added
- Menu link for superusers to admin panel
### Fixed
- Being able to delete ip addresses from nodes

## 2025-07-04
### Added
- Cables and Services now support setting tags. Tags can be used to add information such as raman or long_distance for fibres, which is useful information to the NOC.

## 2025-06-25
### Fixed
- noclook_snap_consumer now checks if a machine is virtual before setting a dependency

## 2025-06-18
### Fixed
- noclook_snap_consumer now handles service ip lists

## 2025-04-09
### Added
- IPCLOS service endpoint in the API

## 2024-11-29
### Added
- Support for import of Rooms (before they were not created as proper Locations)
### Changed
- Major bump, django 4.2 and updated some dependencies, to use you need to update your venv/installtion by reinstalling and updating using `pip install -U -r requirements/prod.txt`

## 2024-10-01
### Added
- Functionality for better handling of multiple IdPs and discovery.
- A new `ModifiedSaml2Backend` has been added, and is used per default if SAML is enabled. With it you can set the `ENABLE_AUTHORIZATION_BY_FILE` and specify a `AUTH_GROUP_FILE`.

## 2024-04-09
### Added
- ODFs now has the bulk port edit functionality

## 2024-02-09
### Changed
- Api when not using pk in resource_uri2id it also uses the resource_name as node_type slug. Should fix the problem SUNET is having with using the API to associate customer, when customernames are overloaded.

## 2024-01-22
### Changed
- sunet_json importer should no longer blow up on the new format

## 2024-01-04
### Added
- `noclook_snap_consumer.py` now tries to depend hosts based on ntnx cluster, ignores unknown clusters


## 2023-11-22
### Added
- Docker Image node type
### Fixed
- Cypher error on host user detail page

## 2023-05-26
### Changed
- Add script for setting customer on all backbon ip services

## 2023-05-17
### Changed
- Fix problem with noclook_producer script that is used for backing up ni

## 2023-05-12
### Changed
- Update clone script to use external script if present

## 2023-05-02
### Changed
- Update djangosaml2 dependency to get rid of XSS

## 2023-04-25
### Changed
- the clone script has been updated to support neo4j running in docker

## 2023-03-27
### Added
- New script `noclook_bulk_service.py` allows bulk creation of services, which at times is useful.

## 2023-03-24
### Changed
- Now suppors neo4j 4.4

## 2023-03-02
### Changed
- Cable API endpoint now supports, spaces, parenthesis and slashes, due to vendor naming schemes.

## 2023-02-15
### Changed
- Make the `noclook_juniper_consumer.py` ignore non suppored nerds data

## 2023-02-06
### Added
- New consumer for sunet json based host import.
- Docker images added to host detail if present.

## 2023-02-01
### Added
- EVPN service endpoint at `/api/v1/evpn/` will be used by NCS/NSO for creating evpn services

## 2023-01-30
- Switch detail view now use the same table as routers for showing interfaces, which includes units

## 2022-11-03
- API cable resources now has a oms_cables subresource, that returns all other cables that are part of the same OMS as the cable. e.g. `/api/v1/cable/NU-0012065/oms_cables/`
- docker compose has changed in version 2, so changes has been made to the `docker/db-restore.sh` script.

## 2022-09-12
### Added
- API now has a ticketinfo sub resource that shows service IDs, and impacted users for cables.

## 2022-01-21
### Added
- The full site list now also shows the site owner ids.

## 2021-11-01
## Added
- Service Ticket Info button containing Service ID, description and affected users for easier ticket creation.
- Requires a collect static for updates to CSS.

## 2021-10-12
## Fixed
- Python 3.10 should now work.

## 2021-10-07

This release migrates to django 3.2 the newest LTS version of django, therefore be sure to update your virtual enviornments as well as run migrations.
Due to dependencies python 3.10 is currently not supported.

### Removed
- python 2 support (EOL 1. jan 2020, and django 3.x does not support it)
  - Removed python_2_unicode_compatible

### Changed
- Migrated to django 3.2 LTS
- Updated dependencies

##  2021-06-03
### Changed
- Use typeahead search instead of dropdowns for location:
  - New External Equipment
  - New Hosts
  - New ODFs
  - New Optical node
- Fix new ODF form
- The location search now searches both sites and racks


## 2021-06-02
### Added
- Rack links can now highlight specific units, linking to `/rack/<rack_id>/#U1,U30-U34` will highlight equipment in unit 1, and 30, 31, 32, 33, 34.
- Units are now listed on ports details
- Expired units can be deleted directly from the port details page.

### Changed
- Switched physical dependency (optical ports connections) to use typeahead search
- noclook_juniper_consume does not filter out fxp ports any more

## 2021-04-27
### Added
- Sites now have a floorplan, where you can place racks.

## 2020-09-10
### Changed
- Site views had a bug with showing rooms, where if there were no rooms it would still show a filter field. Additionally the ID for the table was wrong.

## 2020-07-15
### Added
- Cable reports for racks. Now you can download a csv or excel file with all equipment in the rack cables.

## 2020-06-25
### Added
- Back side to racks. Allowing you to specify if equipment orientation.
- Cable alternative name for tele2 ids, this needs to be change to be more dynamic at some point.
- Owners column to equipment list

### Changed
- Docker image needed pip3, since alpine has split that out to a seperate package.

## 2020-03-17
### Added
- The ability to change which saml backend class to use for authentication - set using `SAML_BACKEND`
- NDNOnly saml backend

## 2020-02-11
### Fixed
- Typeahead search had a problem with `-` in python 3 due to bad regex escaping.

## 2020-02-06
### Added
- Download link for router hardware info

### Changed
- Juniper consumer logs deleted relations better

### Fixed
- Userprofile links (created, modified)

## 2020-01-28
### Changed
- Juniper consumer now creates peering partners without AS numbers, if the description is not missing.
- noclook_consume.py restore script speed ups

### Fix
- SAML2 login from different domains works again, stopped working due to django 2+ setting same site cookies lax

## 2020-01-24
### Added
- Trunk cable creation on patch panels edit

## 2020-01-16

### Fixed
- Comments module has been updated to latest (v1.9.2) to support django 2.2

