=====
Usage
=====

The most basic use of `os-service-types` in a project:

.. code-block:: python

    import os_service_types

    service_types = os_service_types.ServiceTypes()

However, `os-service-types` expects to be able to fetch remote data, so it's
better to pass in a ``Session`` object. Both
:class:`requests.sessions.Session` and
:class:`keystoneauth1.session.Session` objects are supported. A
:class:`keystoneauth1.session.Session` object does not need auth information
attached, although it will not break anything if it does.

.. code-block:: python

    import keystoneauth1.session
    import os_service_types

    session = keystoneauth1.session.Session()
    service_types = os_service_types.ServiceTypes(session=session)
