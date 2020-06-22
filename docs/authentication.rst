Authentication
==============

Opencast supports two types of authentication which can be used by pyCA:

- (Backend) HTTP Digest authentication which is historically used for machine-to-machine communication.
- (General) HTTP Basic (or session-based) authentication used for both front-end users and integrations.

HTTP Digest authentication is the legacy option for capture agents.
It is still widely used today and will continue to be supported.
HTTP Digest is more complicated and has the disadvantage that users need to be specified separately in the backend.

HTTP Basic authentication can be used with users defined via web-interface or via any regular user provider.

PyCA supports both types of authentication.
Which type is being used can be specified in the configuration file::

    auth_method = 'basic'

Both work just fine but HTTP Basic is simpler and needs less requests.
This makes it perform slightly better.

Whatever authentication method you use, make sure to use the correct type of
Opencast users. Digest users are always marked as such in Opencast and cannot
be created via web interface or REST API.
