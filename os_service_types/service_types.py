# Copyright 2017 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
__all__ = ['ServiceTypes']

import copy

import os_service_types.data

BUILTIN_DATA = os_service_types.data.read_data('service-types.json')
SERVICE_TYPES_URL = "https://service-types.openstack.org/service-types.json"


class ServiceTypes(object):
    """Encapsulation of the OpenStack Service Types Authority data.

    The Service Types Authority data will be either pulled from its remote
    location or from local files as is appropriate.

    If the user passes a Session, remote data will be fetched. If the user
    does not do that, local builtin data will be used.

    :param session: An object that behaves like a `requests.sessions.Session`
        or a `keystoneauth1.session.Session` that provides a get method
        and returns an object that behaves like a `requests.models.Response`.
        Optional. If session is omitted, no remote actions will be performed.
    :param bool only_remote: By default if there is a problem fetching data
        remotely the builtin data will be returned as a fallback. only_remote
        will cause remote failures to raise an error instead of falling back.
        Optional, defaults to False.
    :raises ValueError: If session is None and only_remote is True
    :raises IOError: If session is given and only_remote is True and there is
        an error fetching remote data.
    """

    def __init__(self, session=None, only_remote=False):
        if not session and only_remote:
            raise ValueError(
                "only_remote was requested but no Session was provided.")
        self._service_types_data = BUILTIN_DATA
        if session:
            try:
                response = session.get(SERVICE_TYPES_URL)
                response.raise_for_status()
                self._service_types_data = response.json()
            except IOError:
                # If we can't fetch, fall backto BUILTIN
                if only_remote:
                    raise

        by_project = {}
        for s in self._service_types_data['services']:
            for key in ['project', 'api_reference_project']:
                name = s.get(key)
                if name:
                    by_project[self._canonical_project_name(name)] = s
        self._service_types_data['by_project'] = by_project

    def _canonical_project_name(self, name):
        "Convert repo name to project name."
        if name is None:
            raise ValueError("Empty project name is not allowed")
        # Handle openstack/ prefix going away from STA data
        return name.rpartition('/')[-1]

    @property
    def url(self):
        "The URL from which the data was retrieved."
        return SERVICE_TYPES_URL

    @property
    def version(self):
        "The version of the data."
        return self._service_types_data['version']

    @property
    def forward(self):
        "Mapping service-type names to their aliases."
        return copy.deepcopy(self._service_types_data['forward'])

    @property
    def reverse(self):
        "Mapping aliases to their service-type names."
        return copy.deepcopy(self._service_types_data['reverse'])

    @property
    def services(self):
        "Full service-type data listing."
        return copy.deepcopy(self._service_types_data['services'])

    def get_official_service_data(self, service_type):
        """Get the service data for an official service_type.

        :param str service_type: The official service-type to get data for.
        :returns dict: Service data for the service or None if not found.
        """
        for service in self._service_types_data['services']:
            if service_type == service['service_type']:
                return service
        return None

    def get_service_data(self, service_type):
        """Get the service data for a given service_type.

        :param str service_type: The service-type or alias to get data for.
        :returns dict: Service data for the service or None if not found.
        """
        service_type = self.get_service_type(service_type)
        if not service_type:
            return None
        return self.get_official_service_data(service_type)

    def is_official(self, service_type):
        """Is the given service-type an official service-type?

        :param str service_type: The service-type to test.
        :returns bool: True if it's an official type, False otherwise.
        """
        return self.get_official_service_data(service_type) is not None

    def is_alias(self, service_type):
        """Is the given service-type an alias?

        :param str service_type: The service-type to test.
        :returns bool: True if it's an alias type, False otherwise.
        """
        return service_type in self._service_types_data['reverse']

    def is_known(self, service_type):
        """Is the given service-type an official type or an alias?

        :param str service_type: The service-type to test.
        :returns bool: True if it's a known type, False otherwise.
        """
        return self.is_official(service_type) or self.is_alias(service_type)

    def is_match(self, requested, found):
        """Does a requested service-type match one found in the catalog?

        A requested service-type matches a service-type in the catalog if
        it is either a direct match, if the service-type in the catalog is
        an official type and the requested type is one of its aliases, or
        if the requested type is an official type and the type in the catalog
        is one of its aliases.

        A requested alias cannot match a different alias because there are
        historical implications related to versioning to some historical
        aliases that cannot be safely reasoned about in an automatic fashion.

        :param str requested: A service-type that someone is looking for.
        :param str found: A service-type found in a catalog

        :returns bool: True if the service-type being requested matches the
            entry in the catalog. False if it does not.
        """
        # Exact match
        if requested == found:
            return True

        # Found is official type, requested is one of its aliases
        if requested in self.get_aliases(found):
            return True

        # Found is an alias, requested is an official type
        if requested == self.get_service_type(found):
            return True

        return False

    def get_aliases(self, service_type):
        """Returns the list of aliases for a given official service-type.

        :param str service_type: An official service-type.
        :returns list: List of aliases, or empty list if there are none.
        """
        return self._service_types_data['forward'].get(service_type, [])

    def get_service_type(self, service_type):
        """Given a possible service_type, return the official type.

        :param str service_type: A potential service-type.
        :returns str: The official service-type, or None if there is no match.
        """
        if self.is_official(service_type):
            return service_type
        return self._service_types_data['reverse'].get(service_type)

    def get_all_types(self, service_type):
        """Get a list of official types and all known aliases.

        :param str service_type: The service-type or alias to get data for.
        :returns dict: Service data for the service or None if not found.
        """
        if not self.is_known(service_type):
            return [service_type]
        service_type = self.get_service_type(service_type)
        ret = [service_type]
        ret.extend(self.get_aliases(service_type))
        return ret

    def get_project_name(self, service_type):
        """Return the OpenStack project name for a given service_type.

        :param str service_type: An official service-type or alias.
        :returns str: The OpenStack project name or None if there is no match.
        """
        service = self.get_service_data(service_type)
        if service:
            return self._canonical_project_name(service['project'])
        return None

    def get_service_data_for_project(self, project_name):
        """Return the service information associated with a project.

        :param name: A repository or project name in the form
            ``'openstack/{project}'`` or just ``'{project}'``.
        :type name: str
        :returns: dict or None if not found
        """
        key = self._canonical_project_name(project_name)
        return self._service_types_data['by_project'].get(key)
