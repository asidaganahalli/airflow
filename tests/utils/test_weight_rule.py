#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

import unittest

import pytest

from airflow.utils.weight_rule import WeightRule


class TestWeightRule(unittest.TestCase):
    def test_valid_weight_rules(self):
        assert WeightRule.is_valid(WeightRule.DOWNSTREAM)
        assert WeightRule.is_valid(WeightRule.UPSTREAM)
        assert WeightRule.is_valid(WeightRule.ABSOLUTE)
        assert len(WeightRule.all_weight_rules()) == 3

        with pytest.raises(ValueError):
            WeightRule("NOT_EXIST_WEIGHT_RULE")
