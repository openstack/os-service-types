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

from typing import TypedDict

from typing_extensions import NotRequired, Required


class Service(TypedDict, total=False):
    aliases: NotRequired[list[str]]
    api_reference: Required[str]
    project: Required[str]
    service_type: Required[str]


class ServiceTypes(TypedDict):
    all_types_by_service_type: Required[dict[str, list[str]]]
    forward: Required[dict[str, list[str]]]
    primary_service_by_project: Required[dict[str, Service]]
    reverse: Required[dict[str, str]]
    service_types_by_project: Required[dict[str, list[str]]]
    services: Required[list[Service]]
    sha: Required[str]
    version: Required[str]
