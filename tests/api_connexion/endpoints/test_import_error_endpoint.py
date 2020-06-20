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

from parameterized import parameterized

from airflow.models.errors import ImportError  # pylint: disable=redefined-builtin
from airflow.utils import timezone
from airflow.utils.session import provide_session
from airflow.www import app
from tests.test_utils.db import clear_db_import_errors


class TestBaseImportError(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.app = app.create_app(testing=True)  # type:ignore

    def setUp(self) -> None:
        super().setUp()
        self.client = self.app.test_client()  # type:ignore
        self.timestamp = "2020-06-10T12:00"
        clear_db_import_errors()

    def tearDown(self) -> None:
        clear_db_import_errors()

    @staticmethod
    def _normalize_import_errors(import_errors):
        for i, import_error in enumerate(import_errors, 1):
            import_error["import_error_id"] = i


class TestGetImportErrorEndpoint(TestBaseImportError):
    @provide_session
    def test_response_200(self, session):
        import_error = ImportError(
            filename="Lorem_ipsum.py",
            stacktrace="Lorem ipsum",
            timestamp=timezone.parse(self.timestamp, timezone="UTC"),
        )
        session.add(import_error)
        session.commit()

        response = self.client.get(f"/api/v1/importErrors/{import_error.id}")

        assert response.status_code == 200
        response_data = response.json
        response_data["import_error_id"] = 1
        self.assertEqual(
            {
                "filename": "Lorem_ipsum.py",
                "import_error_id": 1,
                "stack_trace": "Lorem ipsum",
                "timestamp": "2020-06-10T12:00:00+00:00",
            },
            response_data,
        )

    def test_response_404(self):
        response = self.client.get("/api/v1/importErrors/2")
        assert response.status_code == 404
        self.assertEqual(
            {
                "detail": None,
                "status": 404,
                "title": "Import error not found",
                "type": "about:blank",
            },
            response.json,
        )


class TestGetImportErrorsEndpoint(TestBaseImportError):
    @provide_session
    def test_get_import_errors(self, session):
        import_error = [
            ImportError(
                filename="Lorem_ipsum.py",
                stacktrace="Lorem ipsum",
                timestamp=timezone.parse(self.timestamp, timezone="UTC"),
            )
            for _ in range(2)
        ]
        session.add_all(import_error)
        session.commit()

        response = self.client.get("/api/v1/importErrors")

        assert response.status_code == 200
        response_data = response.json
        self._normalize_import_errors(response_data['import_errors'])
        self.assertEqual(
            {
                "import_errors": [
                    {
                        "filename": "Lorem_ipsum.py",
                        "import_error_id": 1,
                        "stack_trace": "Lorem ipsum",
                        "timestamp": "2020-06-10T12:00:00+00:00",
                    },
                    {
                        "filename": "Lorem_ipsum.py",
                        "import_error_id": 2,
                        "stack_trace": "Lorem ipsum",
                        "timestamp": "2020-06-10T12:00:00+00:00",
                    },
                ],
                "total_entries": 2,
            },
            response_data,
        )


class TestGetImportErrorsEndpointPagination(TestBaseImportError):
    @parameterized.expand(
        [
            # Limit test data
            ("/api/v1/importErrors?limit=1", ["/tmp/file_1.py"]),
            ("/api/v1/importErrors?limit=100", [f"/tmp/file_{i}.py" for i in range(1, 101)]),
            # Offset test data
            ("/api/v1/importErrors?offset=1", [f"/tmp/file_{i}.py" for i in range(2, 102)]),
            ("/api/v1/importErrors?offset=3", [f"/tmp/file_{i}.py" for i in range(4, 104)]),
            # Limit and offset test data
            ("/api/v1/importErrors?offset=3&limit=3", [f"/tmp/file_{i}.py" for i in [4, 5, 6]]),
        ]
    )
    @provide_session
    def test_limit_and_offset(self, url, expected_import_error_ids, session):
        import_errors = [
            ImportError(
                filename=f"/tmp/file_{i}.py",
                stacktrace="Lorem ipsum",
                timestamp=timezone.parse(self.timestamp, timezone="UTC"),
            )
            for i in range(1, 110)
        ]
        session.add_all(import_errors)
        session.commit()

        response = self.client.get(url)

        assert response.status_code == 200
        import_ids = [
            pool["filename"] for pool in response.json["import_errors"]
        ]
        self.assertEqual(import_ids, expected_import_error_ids)

    @provide_session
    def test_should_respect_default_page_limit(self, session):
        import_errors = [
            ImportError(
                filename=f"/tmp/file_{i}.py",
                stacktrace="Lorem ipsum",
                timestamp=timezone.parse(self.timestamp, timezone="UTC"),
            )
            for i in range(1, 110)
        ]
        session.add_all(import_errors)
        session.commit()
        response = self.client.get("/api/v1/importErrors")
        assert response.status_code == 200
        self.assertEqual(len(response.json['import_errors']), 100)

    @provide_session
    def test_should_raise_when_page_size_limit_exceeded(self, session):
        import_errors = [
            ImportError(
                filename=f"/tmp/file_{i}.py",
                stacktrace="Lorem ipsum",
                timestamp=timezone.parse(self.timestamp, timezone="UTC"),
            )
            for i in range(1, 110)
        ]
        session.add_all(import_errors)
        session.commit()
        response = self.client.get("/api/v1/importErrors?limit=150")
        assert response.status_code == 400
        self.assertEqual(
            response.json,
            {
                'detail': "150 is greater than the maximum of 100\n"
                          "\nFailed validating 'maximum' in schema:\n    "
                          "{'default': 100, 'maximum': 100, "
                          "'minimum': 1, 'type': 'integer'}\n"
                          "\nOn instance:\n    150",
                'status': 400,
                'title': 'Bad Request',
                'type': 'about:blank'
            }

        )
