# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).


## [Unreleased]

## 20202-07-15
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

