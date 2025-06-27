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

import copy
from typing import TYPE_CHECKING, Optional, overload

import os_service_types.data
from os_service_types import exc
from os_service_types import types

if TYPE_CHECKING:
    from requests import sessions

__all__ = ['ServiceTypes']

BUILTIN_DATA = os_service_types.data.read_data('service-types.json')
SERVICE_TYPES_URL = "https://service-types.openstack.org/service-types.json"


@overload
def _normalize_type(service_type: str) -> str: ...


@overload
def _normalize_type(service_type: None) -> None: ...


def _normalize_type(service_type: str | None) -> str | None:
    if not service_type:
        # TODO(stephenfin): This should be an error
        return None
    return service_type.replace('_', '-')


class ServiceTypes:
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
    :param bool warn: Emit warnings when a non-official service_type is
        provided. This provides an easy way for consuming applications to
        warn users when they are using old types.
    :raises ValueError: If session is None and only_remote is True
    :raises IOError: If session is given and only_remote is True and there is
        an error fetching remote data.
    """

    def __init__(
        self,
        session: Optional['sessions.Session'] = None,
        only_remote: bool = False,
        warn: bool = False,
    ) -> None:
        if not session and only_remote:
            raise ValueError(
                "only_remote was requested but no Session was provided."
            )
        self._service_types_data: types.ServiceTypes = BUILTIN_DATA
        self._warn = warn
        if session:
            try:
                response = session.get(SERVICE_TYPES_URL)
                response.raise_for_status()
                self._service_types_data = response.json()
            except OSError:
                # If we can't fetch, fall backto BUILTIN
                if only_remote:
                    raise

    def _canonical_project_name(self, name: str | None) -> str:
        "Convert repo name to project name."
        if name is None:
            raise ValueError("Empty project name is not allowed")
        # Handle openstack/ prefix going away from STA data
        return name.rpartition('/')[-1]

    @property
    def url(self) -> str:
        "The URL from which the data was retrieved."
        return SERVICE_TYPES_URL

    @property
    def version(self) -> str:
        "The version of the data."
        return self._service_types_data['version']

    @property
    def forward(self) -> dict[str, list[str]]:
        "Mapping service-type names to their aliases."
        return copy.deepcopy(self._service_types_data['forward'])

    @property
    def reverse(self) -> dict[str, str]:
        "Mapping aliases to their service-type names."
        return copy.deepcopy(self._service_types_data['reverse'])

    @property
    def services(self) -> list[types.Service]:
        "Full service-type data listing."
        return copy.deepcopy(self._service_types_data['services'])

    @property
    def all_types_by_service_type(self) -> dict[str, list[str]]:
        "Mapping of official service type to official type and aliases."
        return copy.deepcopy(
            self._service_types_data['all_types_by_service_type']
        )

    @property
    def primary_service_by_project(self) -> dict[str, types.Service]:
        "Mapping of project name to the primary associated service."
        return copy.deepcopy(
            self._service_types_data['primary_service_by_project']
        )

    @property
    def service_types_by_project(self) -> dict[str, list[str]]:
        "Mapping of project name to a list of all associated service-types."
        return copy.deepcopy(
            self._service_types_data['service_types_by_project']
        )

    def get_official_service_data(
        self, service_type: str
    ) -> types.Service | None:
        """Get the service data for an official service_type.

        :param str service_type: The official service-type to get data for.
        :returns dict: Service data for the service or None if not found.
        """
        service_type = _normalize_type(service_type)
        for service in self._service_types_data['services']:
            if service_type == service['service_type']:
                return service
        return None

    def get_service_data(self, service_type: str) -> types.Service | None:
        """Get the service data for a given service_type.

        :param str service_type: The service-type or alias to get data for.
        :returns dict: Service data for the service or None if not found.
        """
        official_service_type = self.get_service_type(service_type)
        if not official_service_type:
            return None
        return self.get_official_service_data(official_service_type)

    def is_official(self, service_type: str) -> bool:
        """Is the given service-type an official service-type?

        :param str service_type: The service-type to test.
        :returns bool: True if it's an official type, False otherwise.
        """
        return self.get_official_service_data(service_type) is not None

    def is_alias(self, service_type: str) -> bool:
        """Is the given service-type an alias?

        :param str service_type: The service-type to test.
        :returns bool: True if it's an alias type, False otherwise.
        """
        service_type = _normalize_type(service_type)
        return service_type in self._service_types_data['reverse']

    def is_known(self, service_type: str) -> bool:
        """Is the given service-type an official type or an alias?

        :param str service_type: The service-type to test.
        :returns bool: True if it's a known type, False otherwise.
        """
        return self.is_official(service_type) or self.is_alias(service_type)

    def is_match(self, requested: str, found: str) -> bool:
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

    def get_aliases(self, service_type: str) -> list[str]:
        """Returns the list of aliases for a given official service-type.

        :param service_type: An official service-type.
        :returns: List of aliases, or empty list if there are none.
        """
        service_type = _normalize_type(service_type)
        return self._service_types_data['forward'].get(service_type, [])

    def get_service_type(
        self, service_type: str, permissive: bool = False
    ) -> str | None:
        """Given a possible service_type, return the official type.

        :param service_type: A potential service-type.
        :param permissive:
            Return the original type if the given service_type is not found.
        :returns: The official service-type, or None if there is no match.
        """
        service_type = _normalize_type(service_type)
        if self.is_official(service_type):
            return service_type
        official = self._service_types_data['reverse'].get(service_type)
        if permissive and official is None:
            if self._warn:
                exc.warn(exc.UnofficialUsageWarning, given=service_type)
            return service_type
        if self._warn:
            exc.warn(
                exc.AliasUsageWarning, given=service_type, official=official
            )
        return official

    def get_all_types(self, service_type: str) -> list[str]:
        """Get a list of official types and all known aliases.

        :param str service_type: The service-type or alias to get data for.
        :returns dict: Service data for the service or None if not found.
        """
        service_type = _normalize_type(service_type)
        if not self.is_known(service_type):
            return [service_type]
        official_service_type = self.get_service_type(service_type)
        assert official_service_type is not None
        return self.all_types_by_service_type[official_service_type]

    def get_project_name(self, service_type: str) -> str | None:
        """Return the OpenStack project name for a given service_type.

        :param str service_type: An official service-type or alias.
        :returns: The OpenStack project name or None if there is no match.
        """
        service_type = _normalize_type(service_type)
        service = self.get_service_data(service_type)
        if service:
            return service['project']
        return None

    def get_service_data_for_project(
        self, project_name: str
    ) -> types.Service | None:
        """Return the service information associated with a project.

        :param name: A repository or project name in the form
            ``'openstack/{project}'`` or just ``'{project}'``.
        :type name: str
        :raises ValueError: If project_name is None
        :returns: dict or None if not found
        """
        project_name = self._canonical_project_name(project_name)
        return self.primary_service_by_project.get(project_name)

    def get_all_service_data_for_project(
        self, project_name: str
    ) -> list[types.Service]:
        """Return the information for every service associated with a project.

        :param name: A repository or project name in the form
            ``'openstack/{project}'`` or just ``'{project}'``.
        :type name: str
        :raises ValueError: If project_name is None
        :returns: list of dicts
        """
        data = []
        for service_type in self.service_types_by_project.get(
            project_name, []
        ):
            service = self.get_service_data(service_type)
            if service:
                data.append(service)
        return data
