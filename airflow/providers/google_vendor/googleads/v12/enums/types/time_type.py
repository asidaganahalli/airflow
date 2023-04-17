# -*- coding: utf-8 -*-
# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import proto  # type: ignore


__protobuf__ = proto.module(
    package="airflow.providers.google_vendor.googleads.v12.enums",
    marshal="google.ads.googleads.v12",
    manifest={"TimeTypeEnum",},
)


class TimeTypeEnum(proto.Message):
    r"""Message describing time types.
    """

    class TimeType(proto.Enum):
        r"""The possible time types used by certain resources as an
        alternative to absolute timestamps.
        """
        UNSPECIFIED = 0
        UNKNOWN = 1
        NOW = 2
        FOREVER = 3


__all__ = tuple(sorted(__protobuf__.manifest))
