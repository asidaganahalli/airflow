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
"""This module contains Google Dataproc triggers."""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any, AsyncIterator, Sequence

from google.api_core.exceptions import NotFound
from google.cloud.dataproc_v1 import Batch, Cluster, ClusterStatus, JobStatus

from airflow.providers.google.cloud.hooks.dataproc import DataprocAsyncHook
from airflow.providers.google.cloud.utils.dataproc import DataprocOperationType
from airflow.providers.google.common.hooks.base_google import PROVIDE_PROJECT_ID
from airflow.triggers.base import BaseTrigger, TriggerEvent


class DataprocBaseTrigger(BaseTrigger):
    """Base class for Dataproc triggers."""

    def __init__(
        self,
        region: str,
        project_id: str = PROVIDE_PROJECT_ID,
        gcp_conn_id: str = "google_cloud_default",
        impersonation_chain: str | Sequence[str] | None = None,
        polling_interval_seconds: int = 30,
        delete_on_error: bool = True,
    ):
        super().__init__()
        self.region = region
        self.project_id = project_id
        self.gcp_conn_id = gcp_conn_id
        self.impersonation_chain = impersonation_chain
        self.polling_interval_seconds = polling_interval_seconds
        self.delete_on_error = delete_on_error

    def get_async_hook(self):
        return DataprocAsyncHook(
            gcp_conn_id=self.gcp_conn_id,
            impersonation_chain=self.impersonation_chain,
        )


class DataprocSubmitTrigger(DataprocBaseTrigger):
    """
    DataprocSubmitTrigger run on the trigger worker to perform create Build operation.

    :param job_id: The ID of a Dataproc job.
    :param project_id: Google Cloud Project where the job is running
    :param region: The Cloud Dataproc region in which to handle the request.
    :param gcp_conn_id: Optional, the connection ID used to connect to Google Cloud Platform.
    :param impersonation_chain: Optional service account to impersonate using short-term
        credentials, or chained list of accounts required to get the access_token
        of the last account in the list, which will be impersonated in the request.
        If set as a string, the account must grant the originating account
        the Service Account Token Creator IAM role.
        If set as a sequence, the identities from the list must grant
        Service Account Token Creator IAM role to the directly preceding identity, with first
        account from the list granting this role to the originating account (templated).
    :param polling_interval_seconds: polling period in seconds to check for the status
    """

    def __init__(self, job_id: str, **kwargs):
        self.job_id = job_id
        super().__init__(**kwargs)

    def serialize(self):
        return (
            "airflow.providers.google.cloud.triggers.dataproc.DataprocSubmitTrigger",
            {
                "job_id": self.job_id,
                "project_id": self.project_id,
                "region": self.region,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "polling_interval_seconds": self.polling_interval_seconds,
            },
        )

    async def run(self):
        while True:
            job = await self.get_async_hook().get_job(
                project_id=self.project_id, region=self.region, job_id=self.job_id
            )
            state = job.status.state
            self.log.info("Dataproc job: %s is in state: %s", self.job_id, state)
            if state in (JobStatus.State.DONE, JobStatus.State.CANCELLED, JobStatus.State.ERROR):
                break
            await asyncio.sleep(self.polling_interval_seconds)
        yield TriggerEvent({"job_id": self.job_id, "job_state": state, "job": job})


class DataprocClusterTrigger(DataprocBaseTrigger):
    """
    DataprocClusterTrigger run on the trigger worker to perform create Build operation.

    :param cluster_name: The name of the cluster.
    :param project_id: Google Cloud Project where the job is running
    :param region: The Cloud Dataproc region in which to handle the request.
    :param gcp_conn_id: Optional, the connection ID used to connect to Google Cloud Platform.
    :param impersonation_chain: Optional service account to impersonate using short-term
        credentials, or chained list of accounts required to get the access_token
        of the last account in the list, which will be impersonated in the request.
        If set as a string, the account must grant the originating account
        the Service Account Token Creator IAM role.
        If set as a sequence, the identities from the list must grant
        Service Account Token Creator IAM role to the directly preceding identity, with first
        account from the list granting this role to the originating account (templated).
    :param polling_interval_seconds: polling period in seconds to check for the status
    """

    def __init__(self, cluster_name: str, **kwargs):
        super().__init__(**kwargs)
        self.cluster_name = cluster_name

    def serialize(self) -> tuple[str, dict[str, Any]]:
        return (
            "airflow.providers.google.cloud.triggers.dataproc.DataprocClusterTrigger",
            {
                "cluster_name": self.cluster_name,
                "project_id": self.project_id,
                "region": self.region,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "polling_interval_seconds": self.polling_interval_seconds,
                "delete_on_error": self.delete_on_error,
            },
        )

    async def run(self) -> AsyncIterator[TriggerEvent]:
        """Run the trigger."""
        try:
            while True:
                cluster = await self.fetch_cluster_status()
                if self.check_cluster_state(cluster.status.state):
                    if cluster.status.state == ClusterStatus.State.ERROR:
                        await self.gather_diagnostics_and_maybe_delete(cluster)
                    else:
                        yield TriggerEvent(
                            {
                                "cluster_name": self.cluster_name,
                                "cluster_state": cluster.status.state,
                                "cluster": cluster,
                            }
                        )
                    break
                self.log.info("Sleeping for %s seconds.", self.polling_interval_seconds)
                await asyncio.sleep(self.polling_interval_seconds)
        except asyncio.CancelledError:
            await self.handle_cancellation()

    async def fetch_cluster_status(self) -> Cluster:
        """Fetch the cluster status."""
        return await self.get_async_hook().get_cluster(
            project_id=self.project_id, region=self.region, cluster_name=self.cluster_name
        )

    def check_cluster_state(self, state: ClusterStatus.State) -> bool:
        """
        Check if the state is error or running.

        :param state: The state of the cluster.
        """
        return state in (ClusterStatus.State.ERROR, ClusterStatus.State.RUNNING)

    async def gather_diagnostics_and_maybe_delete(self, cluster: Cluster):
        """
        Gather diagnostics and maybe delete the cluster.

        :param cluster: The cluster to gather diagnostics for.
        """
        self.log.info("Cluster is in ERROR state. Gathering diagnostic information.")
        try:
            operation = await self.get_async_hook().diagnose_cluster(
                region=self.region, cluster_name=self.cluster_name, project_id=self.project_id
            )
            result = await operation.result()
            gcs_uri = str(result.response.value)
            self.log.info(
                "Diagnostic information for cluster %s available at: %s", self.cluster_name, gcs_uri
            )
        except Exception as e:
            self.log.error("Failed to diagnose cluster: %s", e)

        if self.delete_on_error:
            await self.get_async_hook().delete_cluster(
                region=self.region, cluster_name=self.cluster_name, project_id=self.project_id
            )
            return TriggerEvent(
                {
                    "cluster_name": self.cluster_name,
                    "cluster_state": cluster.status.state,
                    "cluster": None,
                    "action": "deleted",
                }
            )
        else:
            return TriggerEvent(
                {"cluster_name": self.cluster_name, "cluster_state": cluster.status.state, "cluster": cluster}
            )

    async def handle_cancellation(self) -> None:
        """Handle the cancellation of the trigger, cleaning up resources if necessary."""
        self.log.info("Cancellation requested. Deleting the cluster if created.")
        try:
            if self.delete_on_error:
                cluster = await self.fetch_cluster_status()
                if cluster.status.state == ClusterStatus.State.ERROR:
                    await self.get_async_hook().async_delete_cluster(
                        region=self.region, cluster_name=self.cluster_name, project_id=self.project_id
                    )
                    self.log.info("Deleted cluster due to ERROR state during cancellation.")
                else:
                    self.log.info("Cancellation did not require cluster deletion.")
        except Exception as e:
            self.log.error("Error during cancellation handling: %s", e)


class DataprocBatchTrigger(DataprocBaseTrigger):
    """
    DataprocCreateBatchTrigger run on the trigger worker to perform create Build operation.

    :param batch_id: The ID of the build.
    :param project_id: Google Cloud Project where the job is running
    :param region: The Cloud Dataproc region in which to handle the request.
    :param gcp_conn_id: Optional, the connection ID used to connect to Google Cloud Platform.
    :param impersonation_chain: Optional service account to impersonate using short-term
        credentials, or chained list of accounts required to get the access_token
        of the last account in the list, which will be impersonated in the request.
        If set as a string, the account must grant the originating account
        the Service Account Token Creator IAM role.
        If set as a sequence, the identities from the list must grant
        Service Account Token Creator IAM role to the directly preceding identity, with first
        account from the list granting this role to the originating account (templated).
    :param polling_interval_seconds: polling period in seconds to check for the status
    """

    def __init__(self, batch_id: str, **kwargs):
        super().__init__(**kwargs)
        self.batch_id = batch_id

    def serialize(self) -> tuple[str, dict[str, Any]]:
        """Serialize DataprocBatchTrigger arguments and classpath."""
        return (
            "airflow.providers.google.cloud.triggers.dataproc.DataprocBatchTrigger",
            {
                "batch_id": self.batch_id,
                "project_id": self.project_id,
                "region": self.region,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "polling_interval_seconds": self.polling_interval_seconds,
            },
        )

    async def run(self):
        while True:
            batch = await self.get_async_hook().get_batch(
                project_id=self.project_id, region=self.region, batch_id=self.batch_id
            )
            state = batch.state

            if state in (Batch.State.FAILED, Batch.State.SUCCEEDED, Batch.State.CANCELLED):
                break
            self.log.info("Current state is %s", state)
            self.log.info("Sleeping for %s seconds.", self.polling_interval_seconds)
            await asyncio.sleep(self.polling_interval_seconds)
        yield TriggerEvent({"batch_id": self.batch_id, "batch_state": state})


class DataprocDeleteClusterTrigger(DataprocBaseTrigger):
    """
    DataprocDeleteClusterTrigger run on the trigger worker to perform delete cluster operation.

    :param cluster_name: The name of the cluster
    :param end_time: Time in second left to check the cluster status
    :param project_id: The ID of the Google Cloud project the cluster belongs to
    :param region: The Cloud Dataproc region in which to handle the request
    :param metadata: Additional metadata that is provided to the method
    :param gcp_conn_id: The connection ID to use when fetching connection info.
    :param impersonation_chain: Optional service account to impersonate using short-term
        credentials, or chained list of accounts required to get the access_token
        of the last account in the list, which will be impersonated in the request.
        If set as a string, the account must grant the originating account
        the Service Account Token Creator IAM role.
        If set as a sequence, the identities from the list must grant
        Service Account Token Creator IAM role to the directly preceding identity, with first
        account from the list granting this role to the originating account.
    :param polling_interval_seconds: Time in seconds to sleep between checks of cluster status
    """

    def __init__(
        self,
        cluster_name: str,
        end_time: float,
        metadata: Sequence[tuple[str, str]] = (),
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self.cluster_name = cluster_name
        self.end_time = end_time
        self.metadata = metadata

    def serialize(self) -> tuple[str, dict[str, Any]]:
        """Serialize DataprocDeleteClusterTrigger arguments and classpath."""
        return (
            "airflow.providers.google.cloud.triggers.dataproc.DataprocDeleteClusterTrigger",
            {
                "cluster_name": self.cluster_name,
                "end_time": self.end_time,
                "project_id": self.project_id,
                "region": self.region,
                "metadata": self.metadata,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "polling_interval_seconds": self.polling_interval_seconds,
            },
        )

    async def run(self) -> AsyncIterator[TriggerEvent]:
        """Wait until cluster is deleted completely."""
        try:
            while self.end_time > time.time():
                cluster = await self.get_async_hook().get_cluster(
                    region=self.region,  # type: ignore[arg-type]
                    cluster_name=self.cluster_name,
                    project_id=self.project_id,  # type: ignore[arg-type]
                    metadata=self.metadata,
                )
                self.log.info(
                    "Cluster status is %s. Sleeping for %s seconds.",
                    cluster.status.state,
                    self.polling_interval_seconds,
                )
                await asyncio.sleep(self.polling_interval_seconds)
        except NotFound:
            yield TriggerEvent({"status": "success", "message": ""})
        except Exception as e:
            yield TriggerEvent({"status": "error", "message": str(e)})
        else:
            yield TriggerEvent({"status": "error", "message": "Timeout"})


class DataprocOperationTrigger(DataprocBaseTrigger):
    """
    Trigger that periodically polls information on a long running operation from Dataproc API to verify status.

    Implementation leverages asynchronous transport.
    """

    def __init__(self, name: str, operation_type: str | None = None, **kwargs: Any):
        super().__init__(**kwargs)
        self.name = name
        self.operation_type = operation_type

    def serialize(self):
        return (
            "airflow.providers.google.cloud.triggers.dataproc.DataprocOperationTrigger",
            {
                "name": self.name,
                "operation_type": self.operation_type,
                "project_id": self.project_id,
                "region": self.region,
                "gcp_conn_id": self.gcp_conn_id,
                "impersonation_chain": self.impersonation_chain,
                "polling_interval_seconds": self.polling_interval_seconds,
            },
        )

    async def run(self) -> AsyncIterator[TriggerEvent]:
        hook = self.get_async_hook()
        try:
            while True:
                operation = await hook.get_operation(region=self.region, operation_name=self.name)
                if operation.done:
                    if operation.error.message:
                        status = "error"
                        message = operation.error.message
                    else:
                        status = "success"
                        message = "Operation is successfully ended."
                    if self.operation_type == DataprocOperationType.DIAGNOSE.value:
                        gcs_regex = rb"gs:\/\/[a-z0-9][a-z0-9_-]{1,61}[a-z0-9_\-\/]*"
                        gcs_uri_value = operation.response.value
                        match = re.search(gcs_regex, gcs_uri_value)
                        if match:
                            output_uri = match.group(0).decode("utf-8", "ignore")
                        else:
                            output_uri = gcs_uri_value
                        yield TriggerEvent(
                            {
                                "status": status,
                                "message": message,
                                "output_uri": output_uri,
                            }
                        )
                    else:
                        yield TriggerEvent(
                            {
                                "operation_name": operation.name,
                                "operation_done": operation.done,
                                "status": status,
                                "message": message,
                            }
                        )
                    return
                else:
                    self.log.info("Sleeping for %s seconds.", self.polling_interval_seconds)
                    await asyncio.sleep(self.polling_interval_seconds)
        except Exception as e:
            self.log.exception("Exception occurred while checking operation status.")
            yield TriggerEvent(
                {
                    "status": "failed",
                    "message": str(e),
                }
            )
