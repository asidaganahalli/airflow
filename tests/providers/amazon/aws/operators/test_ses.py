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
from unittest import mock

from airflow.providers.amazon.aws.operators.ses import SESSendEmailOperator


class TestSESSendEmailOperator(unittest.TestCase):
    @mock.patch('airflow.providers.amazon.aws.operators.ses.SESHook')
    def test_execute(self, mock_hook):
        mock_hook.return_value.send_email.return_value = {}
        operator = SESSendEmailOperator(
            task_id="test-ses",
            mail_from="from@test.com",
            to="to@test.com",
            subject="test-subject",
            html_content="test-content",
            files=["test-file"],
            cc=["cc@test.com"],
            bcc=["bcc@test.com"],
            mime_subtype="mixed",
            mime_charset="utf-8",
            reply_to="reply@test.com",
            return_path=None,
            custom_headers=None,
        )
        result = operator.execute(None)
        assert result == {}
        mock_hook.return_value.send_email.assert_called_with(
            mail_from="from@test.com",
            to="to@test.com",
            subject="test-subject",
            html_content="test-content",
            files=["test-file"],
            cc=["cc@test.com"],
            bcc=["bcc@test.com"],
            mime_subtype="mixed",
            mime_charset="utf-8",
            reply_to="reply@test.com",
            return_path=None,
            custom_headers=None,
        )
