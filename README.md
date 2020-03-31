This is the NORDUnet Network Inventory projects collection of tools and applications.

Some background reading can be found at https://portal.nordu.net/display/NI/NORDUnet+Network+Inventory.

Other components needed:

- neo4j >= 3.4 and < 4.0
- postgresql 9.4 or newer

## Quick up and running in a docker instance

```
$ docker-compose -f docker/compose-dev.yml up
```

Create super user

```
$ docker-compose -f docker/compose-dev.yml run --rm manage createsuperuser
```

# Customisation

Using a dotenv file it is possible to change colors of links and logo, as well as adding branding text see [an example here](src/niweb/dotenv).
