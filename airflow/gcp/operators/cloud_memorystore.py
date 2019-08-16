from typing import Dict, Sequence, Tuple, Union

from google.api_core.retry import Retry
from google.cloud.redis_v1.gapic.enums import FailoverInstanceRequest
from google.cloud.redis_v1.types import FieldMask, InputConfig, Instance, OutputConfig
from google.protobuf.json_format import MessageToDict

from tests.contrib.utils.base_gcp_mock import (GCP_PROJECT_ID_HOOK_UNIT_TEST,
                                               mock_base_gcp_hook_default_project_id,
                                               mock_base_gcp_hook_no_default_project_id)

from airflow.gcp.hooks.cloud_memorystore import CloudMemorystoreHook
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults


class CloudMemorystoreCreateInstanceOperator(BaseOperator):
    """
    Creates a Redis instance based on the specified tier and memory size.

    By default, the instance is accessible from the project's `default network
    <https://cloud.google.com/compute/docs/networks-and-firewalls#networks>`__.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
    :type location: str
    :param instance_id: Required. The logical name of the Redis instance in the customer project with the
        following restrictions:

        -  Must contain only lowercase letters, numbers, and hyphens.
        -  Must start with a letter.
        -  Must be between 1-40 characters.
        -  Must end with a number or a letter.
        -  Must be unique within the customer project / location
    :type instance_id: str
    :param instance: Required. A Redis [Instance] resource

        If a dict is provided, it must be of the same form as the protobuf message
        :class:`~google.cloud.redis_v1.types.Instance`
    :type instance: Union[Dict, google.cloud.redis_v1.types.Instance]
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        instance_id: str,
        instance: Union[Dict, Instance],
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.instance_id = instance_id
        self.instance = instance
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        result = hook.create_instance(
            location=self.location,
            instance_id=self.instance_id,
            instance=self.instance,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
        return MessageToDict(result.result())


class CloudMemorystoreDeleteInstanceOperator(BaseOperator):
    """
    Deletes a specific Redis instance. Instance stops serving and data is deleted.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
    :type location: str
    :param instance: The logical name of the Redis instance in the customer project.
    :type instance: str
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :type project_id: str
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        instance: str,
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.instance = instance
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        result = hook.delete_instance(
            location=self.location,
            instance=self.instance,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
        return MessageToDict(result.result())


class CloudMemorystoreExportInstanceOperator(BaseOperator):
    """
    Export Redis instance data into a Redis RDB format file in Cloud Storage.

    Redis will continue serving during this operation.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
    :type location: str
    :param instance: The logical name of the Redis instance in the customer project.
    :type instance: str
    :param output_config: Required. Specify data to be exported.

        If a dict is provided, it must be of the same form as the protobuf message
        :class:`~google.cloud.redis_v1.types.OutputConfig`
    :type output_config: Union[Dict, google.cloud.redis_v1.types.OutputConfig]
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        instance: str,
        output_config: Union[Dict, OutputConfig],
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.instance = instance
        self.output_config = output_config
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        result = hook.export_instance(
            location=self.location,
            instance=self.instance,
            output_config=self.output_config,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
        return MessageToDict(result.result())


class CloudMemorystoreFailoverInstanceOperator(BaseOperator):
    """
    Initiates a failover of the master node to current replica node for a specific STANDARD tier Cloud
    Memorystore for Redis instance.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
    :type location: str

    :param instance: The logical name of the Redis instance in the customer project.
    :type instance: str
    :param data_protection_mode: Optional. Available data protection modes that the user can choose. If it's
        unspecified, data protection mode will be LIMITED\_DATA\_LOSS by default.
    :type data_protection_mode: google.cloud.redis_v1.gapic.enums.FailoverInstanceRequest.DataProtectionMode
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        instance: str,
        data_protection_mode: FailoverInstanceRequest.DataProtectionMode,
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.instance = instance
        self.data_protection_mode = data_protection_mode
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        result = hook.failover_instance(
            location=self.location,
            instance=self.instance,
            data_protection_mode=self.data_protection_mode,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )

        return MessageToDict(result.result())


class CloudMemorystoreGetInstanceOperator(BaseOperator):
    """
    Gets the details of a specific Redis instance.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
    :type location: str
    :param instance: The logical name of the Redis instance in the customer project.
    :type instance: str
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        instance: str,
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.instance = instance
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        result = hook.get_instance(
            location=self.location,
            instance=self.instance,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
        return MessageToDict(result)


class CloudMemorystoreImportInstanceOperator(BaseOperator):
    """
    Import a Redis RDB snapshot file from Cloud Storage into a Redis instance.

    Redis may stop serving during this operation. Instance state will be IMPORTING for entire operation. When
    complete, the instance will contain only data from the imported file.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
    :type location: str
    :param instance: The logical name of the Redis instance in the customer project.
    :type instance: str
    :param input_config: Required. Specify data to be imported.

        If a dict is provided, it must be of the same form as the protobuf message
        :class:`~google.cloud.redis_v1.types.InputConfig`
    :type input_config: Union[Dict, google.cloud.redis_v1.types.InputConfig]
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        instance: str,
        input_config: Union[Dict, InputConfig],
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.instance = instance
        self.input_config = input_config
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        hook.import_instance(
            location=self.location,
            instance=self.instance,
            input_config=self.input_config,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )


class CloudMemorystoreListInstancesOperator(BaseOperator):
    """
    Lists all Redis instances owned by a project in either the specified location (region) or all locations.

    :param location: The location of the Cloud Memorystore instance (for example europe-west1)
        If it is specified as ``-`` (wildcard), then all regions available to the project are
        queried, and the results are aggregated.
    :type location: str
    :param page_size: The maximum number of resources contained in the underlying API response. If page
        streaming is performed per- resource, this parameter does not affect the return value. If page
        streaming is performed per-page, this determines the maximum number of resources in a page.
    :type page_size: int
    :param project_id: Project ID of the project that contains the instance. If set
        to None or missing, the default project_id from the GCP connection is used.
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        location: str,
        page_size: int,
        project_id: str = None,
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.location = location
        self.page_size = page_size
        self.project_id = project_id
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        result = hook.list_instances(
            location=self.location,
            page_size=self.page_size,
            project_id=self.project_id,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
        instances = [MessageToDict(a) for a in result]
        print(instances)
        return instances


class CloudMemorystoreUpdateInstanceOperator(BaseOperator):
    """
    Updates the metadata and configuration of a specific Redis instance.

    :param update_mask: Required. Mask of fields to update. At least one path must be supplied in this field.
        The elements of the repeated paths field may only include these fields from ``Instance``:

        -  ``displayName``
        -  ``labels``
        -  ``memorySizeGb``
        -  ``redisConfig``

        If a dict is provided, it must be of the same form as the protobuf message
        :class:`~google.cloud.redis_v1.types.FieldMask`
    :type update_mask: Union[Dict, google.cloud.redis_v1.types.FieldMask]
    :param instance: Required. Update description. Only fields specified in update\_mask are updated.

        If a dict is provided, it must be of the same form as the protobuf message
        :class:`~google.cloud.redis_v1.types.Instance`
    :type instance: Union[Dict, google.cloud.redis_v1.types.Instance]
    :param retry: A retry object used to retry requests. If ``None`` is specified, requests will not be
        retried.
    :type retry: google.api_core.retry.Retry
    :param timeout: The amount of time, in seconds, to wait for the request to complete. Note that if
        ``retry`` is specified, the timeout applies to each individual attempt.
    :type timeout: float
    :param metadata: Additional metadata that is provided to the method.
    :type metadata: Sequence[Tuple[str, str]]
    :param gcp_conn_id: The connection ID to use connecting to Google Cloud Platform.
    :type gcp_conn_id: str
    """

    @apply_defaults
    def __init__(
        self,
        update_mask: Union[Dict, FieldMask],
        instance: Union[Dict, Instance],
        retry: Retry = None,
        timeout: float = None,
        metadata: Sequence[Tuple[str, str]] = None,
        gcp_conn_id: str = "google_cloud_default",
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.update_mask = update_mask
        self.instance = instance
        self.retry = retry
        self.timeout = timeout
        self.metadata = metadata
        self.gcp_conn_id = gcp_conn_id

    def execute(self, context: Dict):
        hook = CloudMemorystoreHook(gcp_conn_id=self.gcp_conn_id)
        hook.update_instance(
            update_mask=self.update_mask,
            instance=self.instance,
            retry=self.retry,
            timeout=self.timeout,
            metadata=self.metadata,
        )
