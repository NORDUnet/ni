# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## [Unreleased]

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

