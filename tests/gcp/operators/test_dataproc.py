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

import inspect
import unittest
from datetime import datetime
from typing import Any
from unittest import mock

from google.api_core.exceptions import AlreadyExists
from google.api_core.retry import Retry

from airflow.gcp.operators.dataproc import (
    ClusterGenerator, DataprocClusterCreateOperator, DataprocClusterDeleteOperator,
    DataprocClusterScaleOperator, DataProcHadoopOperator, DataProcHiveOperator, DataProcPigOperator,
    DataProcPySparkOperator, DataProcSparkOperator, DataProcSparkSqlOperator, DataprocSubmitJobOperator,
    DataprocUpdateClusterOperator, DataprocWorkflowTemplateInstantiateInlineOperator,
    DataprocWorkflowTemplateInstantiateOperator,
)
from airflow.version import version as airflow_version

cluster_params = inspect.signature(ClusterGenerator.__init__).parameters

AIRFLOW_VERSION = "v" + airflow_version.replace(".", "-").replace("+", "-")

DATAPROC_PATH = "airflow.gcp.operators.dataproc.{}"

TASK_ID = "task-id"
GCP_PROJECT = "test-project"
GCP_LOCATION = "test-location"
GCP_CONN_ID = "test-conn"

CLUSTER_NAME = "cluster_name"
CLUSTER = {
    "project_id": "project_id",
    "cluster_name": CLUSTER_NAME,
    "config": {
        "gce_cluster_config": {
            "zone_uri": "https://www.googleapis.com/compute/v1/projects/"
                        "project_id/zones/zone",
            "metadata": {"metadata": "data"},
            "network_uri": "network_uri",
            "subnetwork_uri": "subnetwork_uri",
            "internal_ip_only": True,
            "tags": ["tags"],
            "service_account": "service_account",
            "service_account_scopes": ["service_account_scopes"],
        },
        "master_config": {
            "num_instances": 2,
            "machine_type_uri": "https://www.googleapis.com/compute/v1/projects/"
                                "project_id/zones/zone/machineTypes/master_machine_type",
            "disk_config": {
                "boot_disk_type": "master_disk_type",
                "boot_disk_size_gb": 128,
            },
            "image_uri": "https://www.googleapis.com/compute/beta/projects/"
                         "custom_image_project_id/global/images/custom_image",
        },
        "worker_config": {
            "num_instances": 2,
            "machine_type_uri": "https://www.googleapis.com/compute/v1/projects/"
                                "project_id/zones/zone/machineTypes/worker_machine_type",
            "disk_config": {
                "boot_disk_type": "worker_disk_type",
                "boot_disk_size_gb": 256,
            },
            "image_uri": "https://www.googleapis.com/compute/beta/projects/"
                         "custom_image_project_id/global/images/custom_image",
        },
        "secondary_worker_config": {
            "num_instances": 4,
            "machine_type_uri": "https://www.googleapis.com/compute/v1/projects/"
                                "project_id/zones/zone/machineTypes/worker_machine_type",
            "disk_config": {
                "boot_disk_type": "worker_disk_type",
                "boot_disk_size_gb": 256,
            },
            "is_preemptible": True,
        },
        "software_config": {
            "properties": {"properties": "data"},
            "optional_components": ["optional_components"],
        },
        "lifecycle_config": {
            "idle_delete_ttl": "60s",
            "auto_delete_time": "2019-09-12T00:00:00.000000Z",
        },
        "encryption_config": {"gce_pd_kms_key_name": "customer_managed_key"},
        "autoscaling_config": {"policy_uri": "autoscaling_policy"},
        "config_bucket": "storage_bucket",
        "initialization_actions": [
            {"executable_file": "init_actions_uris", "execution_timeout": "600s"}
        ],
    },
    "labels": {"labels": "data", "airflow-version": AIRFLOW_VERSION},
}

UPDATE_MASK = {
    "paths": [
        "config.worker_config.num_instances",
        "config.secondary_worker_config.num_instances",
    ]
}

TIMEOUT = 120
RETRY = mock.MagicMock(Retry)
METADATA = [("key", "value")]
REQUEST_ID = "request_id_uuid"


def assert_warning(msg: str, warning: Any):
    assert any(msg in str(w) for w in warning.warnings)


class TestsClusterGenerator(unittest.TestCase):
    def test_image_version(self):
        with self.assertRaises(AssertionError) as err:
            ClusterGenerator(custom_image="custom_image", image_version="image_version")
            self.assertIn("custom_image and image_version", str(err))

    def test_nodes_number(self):
        with self.assertRaises(AssertionError) as err:
            ClusterGenerator(num_workers=0, num_preemptible_workers=0)
            self.assertIn("num_workers == 0 means single", str(err))

    def test_build(self):
        generator = ClusterGenerator(
            project_id="project_id",
            cluster_name="cluster_name",
            num_workers=2,
            zone="zone",
            network_uri="network_uri",
            subnetwork_uri="subnetwork_uri",
            internal_ip_only=True,
            tags=["tags"],
            storage_bucket="storage_bucket",
            init_actions_uris=["init_actions_uris"],
            init_action_timeout="10m",
            metadata={"metadata": "data"},
            custom_image="custom_image",
            custom_image_project_id="custom_image_project_id",
            autoscaling_policy="autoscaling_policy",
            properties={"properties": "data"},
            optional_components=["optional_components"],
            num_masters=2,
            master_machine_type="master_machine_type",
            master_disk_type="master_disk_type",
            master_disk_size=128,
            worker_machine_type="worker_machine_type",
            worker_disk_type="worker_disk_type",
            worker_disk_size=256,
            num_preemptible_workers=4,
            labels={"labels": "data"},
            region="region",
            service_account="service_account",
            service_account_scopes=["service_account_scopes"],
            idle_delete_ttl=60,
            auto_delete_time=datetime(2019, 9, 12),
            auto_delete_ttl=250,
            customer_managed_key="customer_managed_key",
        )
        cluster = generator.make()
        self.assertDictEqual(CLUSTER, cluster)


class TestDataprocClusterCreateOperator(unittest.TestCase):
    @mock.patch(DATAPROC_PATH.format("inspect.signature"))
    @mock.patch(DATAPROC_PATH.format("ClusterGenerator"))
    def test_depreciation_warning(self, mock_generator, mock_signature):
        mock_signature.return_value.parameters = cluster_params
        with self.assertWarns(DeprecationWarning) as warning:
            DataprocClusterCreateOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                project_id=GCP_PROJECT,
                cluster_name="cluster_name",
                num_workers=2,
                zone="zone",
            )
        assert_warning("Passing cluster parameters by keywords", warning)
        mock_generator.assert_called_once_with(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster_name="cluster_name",
            num_workers=2,
            zone="zone",
        )

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        op = DataprocClusterCreateOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster=CLUSTER,
            request_id=REQUEST_ID,
            gcp_conn_id=GCP_CONN_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.create_cluster.assert_called_once_with(
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster=CLUSTER,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute_if_cluster_exists(self, mock_hook):
        mock_hook.return_value.create_cluster.side_effect = [AlreadyExists("test")]
        op = DataprocClusterCreateOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster=CLUSTER,
            gcp_conn_id=GCP_CONN_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
            request_id=REQUEST_ID,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.create_cluster.assert_called_once_with(
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster=CLUSTER,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )
        mock_hook.return_value.get_cluster.assert_called_once_with(
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster_name=CLUSTER_NAME,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )


class TestDataprocClusterScaleOperator(unittest.TestCase):
    def test_depreciation_warning(self):
        with self.assertWarns(DeprecationWarning) as warning:
            DataprocClusterScaleOperator(
                task_id=TASK_ID, cluster_name=CLUSTER_NAME, project_id=GCP_PROJECT
            )
        assert_warning("DataprocUpdateClusterOperator", warning)

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        cluster_update = {
            "config": {
                "worker_config": {"num_instances": 3},
                "secondary_worker_config": {"num_instances": 4},
            }
        }

        op = DataprocClusterScaleOperator(
            task_id=TASK_ID,
            cluster_name=CLUSTER_NAME,
            project_id=GCP_PROJECT,
            region=GCP_LOCATION,
            num_workers=3,
            num_preemptible_workers=4,
            graceful_decommission_timeout="10m",
            gcp_conn_id=GCP_CONN_ID,
        )
        op.execute(context={})

        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.update_cluster.assert_called_once_with(
            project_id=GCP_PROJECT,
            location=GCP_LOCATION,
            cluster_name=CLUSTER_NAME,
            cluster=cluster_update,
            graceful_decommission_timeout={"seconds": 600},
            update_mask=UPDATE_MASK,
        )


class TestDataprocClusterDeleteOperator(unittest.TestCase):
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        op = DataprocClusterDeleteOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster_name=CLUSTER_NAME,
            request_id=REQUEST_ID,
            gcp_conn_id=GCP_CONN_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.delete_cluster.assert_called_once_with(
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster_name=CLUSTER_NAME,
            cluster_uuid=None,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )


class TestDataprocSubmitJobOperator(unittest.TestCase):
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        job = {}
        job_id = "job_id"
        mock_hook.return_value.wait_for_job.return_value = None
        mock_hook.return_value.submit_job.return_value.reference.job_id = job_id

        op = DataprocSubmitJobOperator(
            task_id=TASK_ID,
            location=GCP_LOCATION,
            project_id=GCP_PROJECT,
            job=job,
            gcp_conn_id=GCP_CONN_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
            request_id=REQUEST_ID,
        )
        op.execute(context={})

        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.submit_job.assert_called_once_with(
            project_id=GCP_PROJECT,
            location=GCP_LOCATION,
            job=job,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )
        mock_hook.return_value.wait_for_job.assert_called_once_with(
            job_id=job_id, project_id=GCP_PROJECT, location=GCP_LOCATION
        )


class TestDataprocUpdateClusterOperator(unittest.TestCase):
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        op = DataprocUpdateClusterOperator(
            task_id=TASK_ID,
            location=GCP_LOCATION,
            cluster_name=CLUSTER_NAME,
            cluster=CLUSTER,
            update_mask=UPDATE_MASK,
            request_id=REQUEST_ID,
            graceful_decommission_timeout={"graceful_decommission_timeout": "600s"},
            project_id=GCP_PROJECT,
            gcp_conn_id=GCP_CONN_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.update_cluster.assert_called_once_with(
            location=GCP_LOCATION,
            project_id=GCP_PROJECT,
            cluster_name=CLUSTER_NAME,
            cluster=CLUSTER,
            update_mask=UPDATE_MASK,
            graceful_decommission_timeout={"graceful_decommission_timeout": "600s"},
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )


class TestDataprocWorkflowTemplateInstantiateOperator(unittest.TestCase):
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        template_id = "template_id"
        version = 6
        parameters = {}

        op = DataprocWorkflowTemplateInstantiateOperator(
            task_id=TASK_ID,
            template_id=template_id,
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            version=version,
            parameters=parameters,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
            gcp_conn_id=GCP_CONN_ID,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.instantiate_workflow_template.assert_called_once_with(
            template_name=template_id,
            location=GCP_LOCATION,
            project_id=GCP_PROJECT,
            version=version,
            parameters=parameters,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )


class TestDataprocWorkflowTemplateInstantiateInlineOperator(unittest.TestCase):
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook):
        template = {}

        op = DataprocWorkflowTemplateInstantiateInlineOperator(
            task_id=TASK_ID,
            template=template,
            region=GCP_LOCATION,
            project_id=GCP_PROJECT,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
            gcp_conn_id=GCP_CONN_ID,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.instantiate_inline_workflow_template.assert_called_once_with(
            template=template,
            location=GCP_LOCATION,
            project_id=GCP_PROJECT,
            request_id=REQUEST_ID,
            retry=RETRY,
            timeout=TIMEOUT,
            metadata=METADATA,
        )


class TestDataProcHiveOperator(unittest.TestCase):
    query = "define sin HiveUDF('sin');"
    variables = {"key": "value"}
    job_id = "uuid_id"
    job = {
        "reference": {
            "project_id": GCP_PROJECT,
            "job_id": "{{task.task_id}}_{{ds_nodash}}_" + job_id,
        },
        "placement": {"cluster_name": "cluster-1"},
        "labels": {"airflow-version": AIRFLOW_VERSION},
        "hive_job": {"query_list": {"queries": [query]}, "script_variables": variables},
    }

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_depreciation_warning(self, mock_hook):
        with self.assertWarns(DeprecationWarning) as warning:
            DataProcHiveOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                query="query",
            )
        assert_warning("DataprocSubmitJobOperator", warning)

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook, mock_uuid):
        mock_uuid.return_value = self.job_id
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_hook.return_value.wait_for_job.return_value = None
        mock_hook.return_value.submit_job.return_value.reference.job_id = self.job_id

        op = DataProcHiveOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            query=self.query,
            variables=self.variables,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.submit_job.assert_called_once_with(
            project_id=GCP_PROJECT, job=self.job, location=GCP_LOCATION
        )
        mock_hook.return_value.wait_for_job.assert_called_once_with(
            job_id=self.job_id, location=GCP_LOCATION, project_id=GCP_PROJECT
        )

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_builder(self, mock_hook, mock_uuid):
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_uuid.return_value = self.job_id

        op = DataProcHiveOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            query=self.query,
            variables=self.variables,
        )
        job = op.generate_job()
        self.assertDictEqual(self.job, job)


class TestDataProcPigOperator(unittest.TestCase):
    query = "define sin HiveUDF('sin');"
    variables = {"key": "value"}
    job_id = "uuid_id"
    job = {
        "reference": {
            "project_id": GCP_PROJECT,
            "job_id": "{{task.task_id}}_{{ds_nodash}}_" + job_id,
        },
        "placement": {"cluster_name": "cluster-1"},
        "labels": {"airflow-version": AIRFLOW_VERSION},
        "pig_job": {"query_list": {"queries": [query]}, "script_variables": variables},
    }

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_depreciation_warning(self, mock_hook):
        with self.assertWarns(DeprecationWarning) as warning:
            DataProcPigOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                query="query",
            )
        assert_warning("DataprocSubmitJobOperator", warning)

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook, mock_uuid):
        mock_uuid.return_value = self.job_id
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_hook.return_value.wait_for_job.return_value = None
        mock_hook.return_value.submit_job.return_value.reference.job_id = self.job_id

        op = DataProcPigOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            query=self.query,
            variables=self.variables,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.submit_job.assert_called_once_with(
            project_id=GCP_PROJECT, job=self.job, location=GCP_LOCATION
        )
        mock_hook.return_value.wait_for_job.assert_called_once_with(
            job_id=self.job_id, location=GCP_LOCATION, project_id=GCP_PROJECT
        )

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_builder(self, mock_hook, mock_uuid):
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_uuid.return_value = self.job_id

        op = DataProcPigOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            query=self.query,
            variables=self.variables,
        )
        job = op.generate_job()
        self.assertDictEqual(self.job, job)


class TestDataProcSparkSqlOperator(unittest.TestCase):
    query = "SHOW DATABASES;"
    variables = {"key": "value"}
    job_id = "uuid_id"
    job = {
        "reference": {
            "project_id": GCP_PROJECT,
            "job_id": "{{task.task_id}}_{{ds_nodash}}_" + job_id,
        },
        "placement": {"cluster_name": "cluster-1"},
        "labels": {"airflow-version": AIRFLOW_VERSION},
        "spark_sql_job": {
            "query_list": {"queries": [query]},
            "script_variables": variables,
        },
    }

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_depreciation_warning(self, mock_hook):
        with self.assertWarns(DeprecationWarning) as warning:
            DataProcSparkSqlOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                query="query",
            )
        assert_warning("DataprocSubmitJobOperator", warning)

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook, mock_uuid):
        mock_uuid.return_value = self.job_id
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_hook.return_value.wait_for_job.return_value = None
        mock_hook.return_value.submit_job.return_value.reference.job_id = self.job_id

        op = DataProcSparkSqlOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            query=self.query,
            variables=self.variables,
        )
        op.execute(context={})
        mock_hook.assert_called_once_with(gcp_conn_id=GCP_CONN_ID)
        mock_hook.return_value.submit_job.assert_called_once_with(
            project_id=GCP_PROJECT, job=self.job, location=GCP_LOCATION
        )
        mock_hook.return_value.wait_for_job.assert_called_once_with(
            job_id=self.job_id, location=GCP_LOCATION, project_id=GCP_PROJECT
        )

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_builder(self, mock_hook, mock_uuid):
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_uuid.return_value = self.job_id

        op = DataProcSparkSqlOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            query=self.query,
            variables=self.variables,
        )
        job = op.generate_job()
        self.assertDictEqual(self.job, job)


class TestDataProcSparkOperator(unittest.TestCase):
    main_class = "org.apache.spark.examples.SparkPi"
    jars = ["file:///usr/lib/spark/examples/jars/spark-examples.jar"]
    job_id = "uuid_id"
    job = {
        "reference": {
            "project_id": GCP_PROJECT,
            "job_id": "{{task.task_id}}_{{ds_nodash}}_" + job_id,
        },
        "placement": {"cluster_name": "cluster-1"},
        "labels": {"airflow-version": AIRFLOW_VERSION},
        "spark_job": {"jar_file_uris": jars, "main_class": main_class},
    }

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_depreciation_warning(self, mock_hook):
        with self.assertWarns(DeprecationWarning) as warning:
            DataProcSparkOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                main_class=self.main_class,
                dataproc_jars=self.jars,
            )
        assert_warning("DataprocSubmitJobOperator", warning)

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook, mock_uuid):
        mock_uuid.return_value = self.job_id
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_uuid.return_value = self.job_id

        op = DataProcSparkOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            main_class=self.main_class,
            dataproc_jars=self.jars,
        )
        job = op.generate_job()
        self.assertDictEqual(self.job, job)


class TestDataProcHadoopOperator(unittest.TestCase):
    args = ["wordcount", "gs://pub/shakespeare/rose.txt"]
    jar = "file:///usr/lib/spark/examples/jars/spark-examples.jar"
    job_id = "uuid_id"
    job = {
        "reference": {
            "project_id": GCP_PROJECT,
            "job_id": "{{task.task_id}}_{{ds_nodash}}_" + job_id,
        },
        "placement": {"cluster_name": "cluster-1"},
        "labels": {"airflow-version": AIRFLOW_VERSION},
        "hadoop_job": {"main_jar_file_uri": jar, "args": args},
    }

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_depreciation_warning(self, mock_hook):
        with self.assertWarns(DeprecationWarning) as warning:
            DataProcHadoopOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                main_jar=self.jar,
                arguments=self.args,
            )
        assert_warning("DataprocSubmitJobOperator", warning)

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook, mock_uuid):
        mock_uuid.return_value = self.job_id
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_uuid.return_value = self.job_id

        op = DataProcHadoopOperator(
            task_id=TASK_ID,
            region=GCP_LOCATION,
            gcp_conn_id=GCP_CONN_ID,
            main_jar=self.jar,
            arguments=self.args,
        )
        job = op.generate_job()
        self.assertDictEqual(self.job, job)


class TestDataProcPySparkOperator(unittest.TestCase):
    uri = "gs://{}/{}"
    job_id = "uuid_id"
    job = {
        "reference": {
            "project_id": GCP_PROJECT,
            "job_id": "{{task.task_id}}_{{ds_nodash}}_" + job_id,
        },
        "placement": {"cluster_name": "cluster-1"},
        "labels": {"airflow-version": AIRFLOW_VERSION},
        "pyspark_job": {"main_python_file_uri": uri},
    }

    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_depreciation_warning(self, mock_hook):
        with self.assertWarns(DeprecationWarning) as warning:
            DataProcPySparkOperator(
                task_id=TASK_ID,
                region=GCP_LOCATION,
                main=self.uri,
            )
        assert_warning("DataprocSubmitJobOperator", warning)

    @mock.patch(DATAPROC_PATH.format("uuid.uuid4"))
    @mock.patch(DATAPROC_PATH.format("DataprocHook"))
    def test_execute(self, mock_hook, mock_uuid):
        mock_hook.return_value.project_id = GCP_PROJECT
        mock_uuid.return_value = self.job_id

        op = DataProcPySparkOperator(
            task_id=TASK_ID, region=GCP_LOCATION, gcp_conn_id=GCP_CONN_ID, main=self.uri
        )
        job = op.generate_job()
        self.assertDictEqual(self.job, job)
