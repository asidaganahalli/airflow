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
from __future__ import annotations

import datetime
import enum
import functools
import hashlib
import time
import traceback
import warnings
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Callable, Iterable

from sqlalchemy import select

from airflow import settings
from airflow.api_internal.internal_api_call import InternalApiConfig, internal_api_call
from airflow.configuration import conf
from airflow.exceptions import (
    AirflowException,
    AirflowPokeFailException,
    AirflowRescheduleException,
    AirflowSensorTimeout,
    AirflowSkipException,
    AirflowTaskTimeout,
    RemovedInAirflow3Warning,
    TaskDeferralError,
)
from airflow.executors.executor_loader import ExecutorLoader
from airflow.models.baseoperator import BaseOperator
from airflow.models.skipmixin import SkipMixin
from airflow.models.taskreschedule import TaskReschedule
from airflow.ti_deps.deps.ready_to_reschedule import ReadyToRescheduleDep
from airflow.utils import timezone

# We need to keep the import here because GCSToLocalFilesystemOperator released in
# Google Provider before 3.0.0 imported apply_defaults from here.
# See  https://github.com/apache/airflow/issues/16035
from airflow.utils.decorators import apply_defaults  # noqa: F401
from airflow.utils.session import NEW_SESSION, provide_session
from airflow.utils.types import NOTSET, ArgNotSet

if TYPE_CHECKING:
    from sqlalchemy.orm.session import Session

    from airflow.utils.context import Context

# As documented in https://dev.mysql.com/doc/refman/5.7/en/datetime.html.
_MYSQL_TIMESTAMP_MAX = datetime.datetime(2038, 1, 19, 3, 14, 7, tzinfo=timezone.utc)


@functools.lru_cache(maxsize=None)
def _is_metadatabase_mysql() -> bool:
    if InternalApiConfig.get_use_internal_api():
        return False
    if settings.engine is None:
        raise AirflowException("Must initialize ORM first")
    return settings.engine.url.get_backend_name() == "mysql"


class PokeReturnValue:
    """
    Optional return value for poke methods.

    Sensors can optionally return an instance of the PokeReturnValue class in the poke method.
    If an XCom value is supplied when the sensor is done, then the XCom value will be
    pushed through the operator return value.
    :param is_done: Set to true to indicate the sensor can stop poking.
    :param xcom_value: An optional XCOM value to be returned by the operator.
    """

    def __init__(self, is_done: bool, xcom_value: Any | None = None) -> None:
        self.xcom_value = xcom_value
        self.is_done = is_done

    def __bool__(self) -> bool:
        return self.is_done


@internal_api_call
@provide_session
def _orig_start_date(
    dag_id: str, task_id: str, run_id: str, map_index: int, try_number: int, session: Session = NEW_SESSION
):
    """
    Get the original start_date for a rescheduled task.

    :meta private:
    """
    return session.scalar(
        select(TaskReschedule)
        .where(
            TaskReschedule.dag_id == dag_id,
            TaskReschedule.task_id == task_id,
            TaskReschedule.run_id == run_id,
            TaskReschedule.map_index == map_index,
            TaskReschedule.try_number == try_number,
        )
        .order_by(TaskReschedule.id.asc())
        .with_only_columns(TaskReschedule.start_date)
        .limit(1)
    )


class FailPolicy(str, enum.Enum):
    """Class with sensor's fail policies."""

    # if poke method raise an exception, sensor will not be skipped on.
    NONE = "none"

    # If poke method raises an exception, sensor will be skipped on.
    SKIP_ON_ANY_ERROR = "skip_on_any_error"

    # If poke method raises AirflowSensorTimeout, AirflowTaskTimeout,AirflowPokeFailException or AirflowSkipException
    # sensor will be skipped on.
    SKIP_ON_TIMEOUT = "skip_on_timeout"

    # If poke method raises an exception different from AirflowSensorTimeout, AirflowTaskTimeout,
    # AirflowSkipException or AirflowFailException sensor will ignore exception and re-poke until timeout.
    IGNORE_ERROR = "ignore_error"


class BaseSensorOperator(BaseOperator, SkipMixin):
    """
    Sensor operators are derived from this class and inherit these attributes.

    Sensor operators keep executing at a time interval and succeed when
    a criteria is met and fail if and when they time out.

    :param soft_fail: deprecated parameter replaced by FailPolicy.SKIP_ON_TIMEOUT
           but that do not skip on AirflowFailException
           Mutually exclusive with fail_policy and silent_fail.
    :param poke_interval: Time that the job should wait in between each try.
        Can be ``timedelta`` or ``float`` seconds.
    :param timeout: Time elapsed before the task times out and fails.
        Can be ``timedelta`` or ``float`` seconds.
        This should not be confused with ``execution_timeout`` of the
        ``BaseOperator`` class. ``timeout`` measures the time elapsed between the
        first poke and the current time (taking into account any
        reschedule delay between each poke), while ``execution_timeout``
        checks the **running** time of the task (leaving out any reschedule
        delay). In case that the ``mode`` is ``poke`` (see below), both of
        them are equivalent (as the sensor is never rescheduled), which is not
        the case in ``reschedule`` mode.
    :param mode: How the sensor operates.
        Options are: ``{ poke | reschedule }``, default is ``poke``.
        When set to ``poke`` the sensor is taking up a worker slot for its
        whole execution time and sleeps between pokes. Use this mode if the
        expected runtime of the sensor is short or if a short poke interval
        is required. Note that the sensor will hold onto a worker slot and
        a pool slot for the duration of the sensor's runtime in this mode.
        When set to ``reschedule`` the sensor task frees the worker slot when
        the criteria is not yet met and it's rescheduled at a later time. Use
        this mode if the time before the criteria is met is expected to be
        quite long. The poke interval should be more than one minute to
        prevent too much load on the scheduler.
    :param exponential_backoff: allow progressive longer waits between
        pokes by using exponential backoff algorithm
    :param max_wait: maximum wait interval between pokes, can be ``timedelta`` or ``float`` seconds
    :param silent_fail: deprecated parameter same effect than FailPolicy.IGNORE_ERROR
           Mutually exclusive with fail_policy and soft_fail.
    :param fail_policy: defines the rule by which sensor skip itself. Options are:
        ``{ none | skip_on_any_error | skip_on_timeout | ignore_error }``
        default is ``none``. Options can be set as string or
        using the constants defined in the static class ``airflow.sensors.base.FailPolicy``
        Mutually exclusive with soft_fail and silent_fail.
    """

    ui_color: str = "#e6f1f2"
    valid_modes: Iterable[str] = ["poke", "reschedule"]

    # Adds one additional dependency for all sensor operators that checks if a
    # sensor task instance can be rescheduled.
    deps = BaseOperator.deps | {ReadyToRescheduleDep()}

    def __init__(
        self,
        *,
        poke_interval: timedelta | float = 60,
        timeout: timedelta | float = conf.getfloat("sensors", "default_timeout"),
        soft_fail: bool = False,
        mode: str = "poke",
        exponential_backoff: bool = False,
        max_wait: timedelta | float | None = None,
        silent_fail: bool = False,
        fail_policy: str | ArgNotSet = NOTSET,  # FailPolicy.NONE,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.poke_interval = self._coerce_poke_interval(poke_interval).total_seconds()
        self.soft_fail = soft_fail
        self.timeout = self._coerce_timeout(timeout).total_seconds()
        self.mode = mode
        self.exponential_backoff = exponential_backoff
        self.max_wait = self._coerce_max_wait(max_wait)
        if fail_policy != NOTSET:
            if sum([soft_fail, silent_fail]) > 0:
                raise ValueError(
                    "fail_policy and deprecated soft_fail and silent_fail parameters are mutually exclusive."
                )

            if fail_policy == FailPolicy.SKIP_ON_TIMEOUT:
                self.soft_fail = True
            elif fail_policy == FailPolicy.IGNORE_ERROR:
                self.silent_fail = True
        else:
            if sum([soft_fail, silent_fail]) > 1:
                raise ValueError(
                    "soft_fail and silent_fail are mutually exclusive, you can not provide more than one."
                )

            if soft_fail:
                warnings.warn(
                    "`soft_fail` is deprecated and will be removed in a future version. "
                    "Please provide fail_policy=FailPolicy.skip_on_timeout instead.",
                    RemovedInAirflow3Warning,
                    stacklevel=3,
                )
                fail_policy = FailPolicy.SKIP_ON_TIMEOUT
            elif silent_fail:
                warnings.warn(
                    "`silent_fail` is deprecated and will be removed in a future version. "
                    "Please provide fail_policy=FailPolicy.IGNORE_ERRORS instead.",
                    RemovedInAirflow3Warning,
                    stacklevel=3,
                )
                fail_policy = FailPolicy.IGNORE_ERROR

            else:
                fail_policy = FailPolicy.NONE

        self.silent_fail = silent_fail
        self.fail_policy = fail_policy
        self._validate_input_values()

    @staticmethod
    def _coerce_poke_interval(poke_interval: float | timedelta) -> timedelta:
        if isinstance(poke_interval, timedelta):
            return poke_interval
        if isinstance(poke_interval, (int, float)) and poke_interval >= 0:
            return timedelta(seconds=poke_interval)
        raise AirflowException(
            "Operator arg `poke_interval` must be timedelta object or a non-negative number"
        )

    @staticmethod
    def _coerce_timeout(timeout: float | timedelta) -> timedelta:
        if isinstance(timeout, timedelta):
            return timeout
        if isinstance(timeout, (int, float)) and timeout >= 0:
            return timedelta(seconds=timeout)
        raise AirflowException("Operator arg `timeout` must be timedelta object or a non-negative number")

    @staticmethod
    def _coerce_max_wait(max_wait: float | timedelta | None) -> timedelta | None:
        if max_wait is None or isinstance(max_wait, timedelta):
            return max_wait
        if isinstance(max_wait, (int, float)) and max_wait >= 0:
            return timedelta(seconds=max_wait)
        raise AirflowException("Operator arg `max_wait` must be timedelta object or a non-negative number")

    def _validate_input_values(self) -> None:
        if not isinstance(self.poke_interval, (int, float)) or self.poke_interval < 0:
            raise AirflowException("The poke_interval must be a non-negative number")
        if not isinstance(self.timeout, (int, float)) or self.timeout < 0:
            raise AirflowException("The timeout must be a non-negative number")
        if self.mode not in self.valid_modes:
            raise AirflowException(
                f"The mode must be one of {self.valid_modes},'{self.dag.dag_id if self.has_dag() else ''} "
                f".{self.task_id}'; received '{self.mode}'."
            )

        # Quick check for poke_interval isn't immediately over MySQL's TIMESTAMP limit.
        # This check is only rudimentary to catch trivial user errors, e.g. mistakenly
        # set the value to milliseconds instead of seconds. There's another check when
        # we actually try to reschedule to ensure database coherence.
        if self.reschedule and _is_metadatabase_mysql():
            if timezone.utcnow() + datetime.timedelta(seconds=self.poke_interval) > _MYSQL_TIMESTAMP_MAX:
                raise AirflowException(
                    f"Cannot set poke_interval to {self.poke_interval} seconds in reschedule "
                    f"mode since it will take reschedule time over MySQL's TIMESTAMP limit."
                )

    def poke(self, context: Context) -> bool | PokeReturnValue:
        """Override when deriving this class."""
        raise AirflowException("Override me.")

    def execute(self, context: Context) -> Any:
        started_at: datetime.datetime | float

        if self.reschedule:
            ti = context["ti"]
            max_tries: int = ti.max_tries or 0
            retries: int = self.retries or 0
            # If reschedule, use the start date of the first try (first try can be either the very
            # first execution of the task, or the first execution after the task was cleared.)
            first_try_number = max_tries - retries + 1
            start_date = _orig_start_date(
                dag_id=ti.dag_id,
                task_id=ti.task_id,
                run_id=ti.run_id,
                map_index=ti.map_index,
                try_number=first_try_number,
            )
            if not start_date:
                start_date = timezone.utcnow()
            started_at = start_date

            def run_duration() -> float:
                # If we are in reschedule mode, then we have to compute diff
                # based on the time in a DB, so can't use time.monotonic
                return (timezone.utcnow() - start_date).total_seconds()

        else:
            started_at = start_monotonic = time.monotonic()

            def run_duration() -> float:
                return time.monotonic() - start_monotonic

        poke_count = 1
        log_dag_id = self.dag.dag_id if self.has_dag() else ""

        xcom_value = None
        while True:
            try:
                poke_return = self.poke(context)
            except (
                AirflowSensorTimeout,
                AirflowTaskTimeout,
                AirflowPokeFailException,
                AirflowSkipException,
            ) as e:
                if self.fail_policy == FailPolicy.SKIP_ON_TIMEOUT:
                    raise AirflowSkipException("Skipping due fail_policy set to SKIP_ON_TIMEOUT.") from e
                elif self.fail_policy == FailPolicy.SKIP_ON_ANY_ERROR:
                    raise AirflowSkipException("Skipping due to SKIP_ON_ANY_ERROR is set to True.") from e
                raise e
            except Exception as e:
                if self.fail_policy == FailPolicy.IGNORE_ERROR:
                    self.log.error("Sensor poke failed: \n %s", traceback.format_exc())
                    poke_return = False
                elif self.fail_policy == FailPolicy.SKIP_ON_ANY_ERROR:
                    raise AirflowSkipException("Skipping due to SKIP_ON_ANY_ERROR is set to True.") from e
                else:
                    raise e

            if poke_return:
                if isinstance(poke_return, PokeReturnValue):
                    xcom_value = poke_return.xcom_value
                break

            if run_duration() > self.timeout:
                # If sensor is in SKIP_ON_TIMEOUT mode but times out it raise AirflowSkipException.
                message = (
                    f"Sensor has timed out; run duration of {run_duration()} seconds exceeds "
                    f"the specified timeout of {self.timeout}."
                )

                if self.fail_policy == FailPolicy.SKIP_ON_TIMEOUT:
                    raise AirflowSkipException(message)
                else:
                    raise AirflowSensorTimeout(message)
            if self.reschedule:
                next_poke_interval = self._get_next_poke_interval(started_at, run_duration, poke_count)
                reschedule_date = timezone.utcnow() + timedelta(seconds=next_poke_interval)
                if _is_metadatabase_mysql() and reschedule_date > _MYSQL_TIMESTAMP_MAX:
                    raise AirflowSensorTimeout(
                        f"Cannot reschedule DAG {log_dag_id} to {reschedule_date.isoformat()} "
                        f"since it is over MySQL's TIMESTAMP storage limit."
                    )
                raise AirflowRescheduleException(reschedule_date)
            else:
                time.sleep(self._get_next_poke_interval(started_at, run_duration, poke_count))
                poke_count += 1
        self.log.info("Success criteria met. Exiting.")
        return xcom_value

    def resume_execution(self, next_method: str, next_kwargs: dict[str, Any] | None, context: Context):
        try:
            return super().resume_execution(next_method, next_kwargs, context)
        except (AirflowException, TaskDeferralError) as e:
            if self.fail_policy == FailPolicy.SKIP_ON_ANY_ERROR:
                raise AirflowSkipException(str(e)) from e
            raise

    def _get_next_poke_interval(
        self,
        started_at: datetime.datetime | float,
        run_duration: Callable[[], float],
        poke_count: int,
    ) -> float:
        """Use similar logic which is used for exponential backoff retry delay for operators."""
        if not self.exponential_backoff:
            return self.poke_interval

        if self.reschedule:
            # Calculate elapsed time since the sensor started
            elapsed_time = run_duration()

            # Initialize variables for the simulation
            cumulative_time: float = 0.0
            estimated_poke_count: int = 0

            while cumulative_time <= elapsed_time:
                estimated_poke_count += 1
                # Calculate min_backoff for the current try number
                min_backoff = max(int(self.poke_interval * (2 ** (estimated_poke_count - 2))), 1)

                # Calculate the jitter
                run_hash = int(
                    hashlib.sha1(
                        f"{self.dag_id}#{self.task_id}#{started_at}#{estimated_poke_count}".encode()
                    ).hexdigest(),
                    16,
                )
                modded_hash = min_backoff + run_hash % min_backoff

                # Calculate the jitter, which is used to prevent multiple sensors simultaneously poking
                interval_with_jitter = min(modded_hash, timedelta.max.total_seconds() - 1)

                # Add the interval to the cumulative time
                cumulative_time += interval_with_jitter

            # Now we have an estimated_poke_count based on the elapsed time
            poke_count = estimated_poke_count or poke_count

        # The value of min_backoff should always be greater than or equal to 1.
        min_backoff = max(int(self.poke_interval * (2 ** (poke_count - 2))), 1)

        run_hash = int(
            hashlib.sha1(f"{self.dag_id}#{self.task_id}#{started_at}#{poke_count}".encode()).hexdigest(),
            16,
        )
        modded_hash = min_backoff + run_hash % min_backoff

        delay_backoff_in_seconds = min(modded_hash, timedelta.max.total_seconds() - 1)
        new_interval = min(self.timeout - int(run_duration()), delay_backoff_in_seconds)

        if self.max_wait:
            new_interval = min(self.max_wait.total_seconds(), new_interval)

        self.log.info("new %s interval is %s", self.mode, new_interval)
        return new_interval

    def prepare_for_execution(self) -> BaseOperator:
        task = super().prepare_for_execution()

        # Sensors in `poke` mode can block execution of DAGs when running
        # with single process executor, thus we change the mode to`reschedule`
        # to allow parallel task being scheduled and executed
        executor, _ = ExecutorLoader.import_default_executor_cls()
        if executor.change_sensor_mode_to_reschedule:
            self.log.warning("%s changes sensor mode to 'reschedule'.", executor.__name__)
            task.mode = "reschedule"
        return task

    @property
    def reschedule(self):
        """Define mode rescheduled sensors."""
        return self.mode == "reschedule"

    @classmethod
    def get_serialized_fields(cls):
        return super().get_serialized_fields() | {"reschedule"}


def poke_mode_only(cls):
    """
    Decorate a subclass of BaseSensorOperator with poke.

    Indicate that instances of this class are only safe to use poke mode.

    Will decorate all methods in the class to assert they did not change
    the mode from 'poke'.

    :param cls: BaseSensor class to enforce methods only use 'poke' mode.
    """

    def decorate(cls_type):
        def mode_getter(_):
            return "poke"

        def mode_setter(_, value):
            if value != "poke":
                raise ValueError(f"Cannot set mode to '{value}'. Only 'poke' is acceptable")

        if not issubclass(cls_type, BaseSensorOperator):
            raise ValueError(
                f"poke_mode_only decorator should only be "
                f"applied to subclasses of BaseSensorOperator,"
                f" got:{cls_type}."
            )

        cls_type.mode = property(mode_getter, mode_setter)

        return cls_type

    return decorate(cls)
