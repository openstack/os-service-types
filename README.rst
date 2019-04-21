================
os-service-types
================

Python library for consuming OpenStack sevice-types-authority data

The `OpenStack Service Types Authority`_ contains information about official
OpenStack services and their historical ``service-type`` aliases.

The data is in JSON and the latest data should always be used. This simple
library exists to allow for easy consumption of the data, along with a built-in
version of the data to use in case network access is for some reason not
possible and local caching of the fetched data.

* Free software: Apache license
* Documentation: https://docs.openstack.org/os-service-types/latest/
* Source: https://opendev.org/openstack/os-service-types
* Bugs: https://storyboard.openstack.org/#!/project/904
* Release notes: https://docs.openstack.org/releasenotes/os-service-types/

.. _OpenStack Service Types Authority: https://service-types.openstack.org/
