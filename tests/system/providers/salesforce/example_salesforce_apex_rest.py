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
from __future__ import annotations

import os
from datetime import datetime

from airflow import DAG
from airflow.providers.salesforce.operators.salesforce_apex_rest import SalesforceApexRestOperator

ENV_ID = os.environ.get("SYSTEM_TESTS_ENV_ID")
DAG_ID = "example_gcs_to_trino"


with DAG(
    dag_id="salesforce_apex_rest_operator_dag",
    schedule_interval=None,
    start_date=datetime(2021, 1, 1),
    catchup=False,
) as dag:

    # [START howto_salesforce_apex_rest_operator]
    payload = {"activity": [{"user": "12345", "action": "update page", "time": "2014-04-21T13:00:15Z"}]}

    apex_operator = SalesforceApexRestOperator(
        task_id="apex_task", method='POST', endpoint='User/Activity', payload=payload
    )
    # [END howto_salesforce_apex_rest_operator]


from tests.system.utils import get_test_run  # noqa: E402

# Needed to run the example DAG with pytest (see: tests/system/README.md#run_via_pytest)
test_run = get_test_run(dag)
