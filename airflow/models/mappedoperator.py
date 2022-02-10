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

import datetime
import unittest.mock
import warnings
from typing import (
    TYPE_CHECKING,
    Any,
    Collection,
    Dict,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
)

import attr
from sqlalchemy import func, or_
from sqlalchemy.orm.session import Session

from airflow.compat.functools import cache
from airflow.models.abstractoperator import AbstractOperator
from airflow.models.param import ParamsDict
from airflow.serialization.enums import DagAttributeTypes
from airflow.ti_deps.deps.base_ti_dep import BaseTIDep
from airflow.ti_deps.deps.mapped_task_expanded import MappedTaskIsExpanded
from airflow.utils import timezone
from airflow.utils.session import NEW_SESSION
from airflow.utils.state import State, TaskInstanceState
from airflow.utils.task_group import TaskGroup

if TYPE_CHECKING:
    from airflow.models.baseoperator import BaseOperator, BaseOperatorLink
    from airflow.models.dag import DAG
    from airflow.models.taskinstance import TaskInstance


def _validate_mapping_kwargs(op: Type["BaseOperator"], func: str, value: Dict[str, Any]) -> None:
    # use a dict so order of args is same as code order
    unknown_args = value.copy()
    for klass in op.mro():
        init = klass.__init__  # type: ignore
        try:
            param_names = init._BaseOperatorMeta__param_names
        except AttributeError:
            continue
        for name in param_names:
            unknown_args.pop(name, None)
        if not unknown_args:
            return  # If we have no args left ot check: stop looking at the MRO chian.
    if len(unknown_args) == 1:
        error = f"unexpected keyword argument {unknown_args.popitem()[0]!r}"
    else:
        names = ", ".join(repr(n) for n in unknown_args)
        error = f"unexpected keyword arguments {names}"
    raise TypeError(f"{op.__name__}.{func}() got {error}")


def prevent_duplicates(kwargs1: Dict[str, Any], kwargs2: Dict[str, Any], *, fail_reason: str) -> None:
    duplicated_keys = set(kwargs1).intersection(kwargs2)
    if not duplicated_keys:
        return
    if len(duplicated_keys) == 1:
        raise TypeError(f"{fail_reason} argument: {duplicated_keys.pop()}")
    duplicated_keys_display = ", ".join(sorted(duplicated_keys))
    raise TypeError(f"{fail_reason} arguments: {duplicated_keys_display}")


@attr.define(kw_only=True, repr=False)
class OperatorPartial:
    """An "intermediate state" returned by ``BaseOperator.partial()``.

    This only exists at DAG-parsing time; the only intended usage is for the
    user to call ``.map()`` on it at some point (usually in a method chain) to
    create a ``MappedOperator`` to add into the DAG.
    """

    operator_class: Type["BaseOperator"]
    kwargs: Dict[str, Any]

    def __attrs_post_init__(self):
        _validate_mapping_kwargs(self.operator_class, "partial", self.kwargs)

    @classmethod
    def from_baseoperator(
        cls,
        operator_class: Type["BaseOperator"],
        *,
        task_id: str,
        dag: Optional["DAG"],
        task_group: Optional["TaskGroup"],
        start_date: Optional[datetime.datetime],
        end_date: Optional[datetime.datetime],
        **kwargs,
    ) -> "OperatorPartial":
        from airflow.models.dag import DagContext
        from airflow.utils.task_group import TaskGroupContext

        _validate_mapping_kwargs(operator_class, "partial", kwargs)

        task_group = task_group or TaskGroupContext.get_current_task_group(dag)
        if task_group:
            task_id = task_group.child_id(task_id)

        # Store these in kwargs so they are automatically excluded from map().
        kwargs["dag"] = dag or DagContext.get_current_dag()
        kwargs["task_group"] = task_group
        kwargs["task_id"] = task_id
        kwargs["start_date"] = timezone.convert_to_utc(start_date)
        kwargs["end_date"] = timezone.convert_to_utc(end_date)

        return cls(operator_class=operator_class, kwargs=kwargs)

    def __repr__(self) -> str:
        args = ", ".join(f"{k}={v!r}" for k, v in self.kwargs.items())
        return f"{self.operator_class.__name__}.partial({args})"

    def __del__(self):
        if "__map_called" not in self.__dict__:
            warnings.warn(f"{self!r} was never mapped!")

    def map(self, **mapped_kwargs) -> "MappedOperator":
        from airflow.operators.dummy import DummyOperator

        _validate_mapping_kwargs(self.operator_class, "map", mapped_kwargs)

        partial_kwargs = self.kwargs.copy()
        task_id = partial_kwargs.pop("task_id")
        params = partial_kwargs.pop("params", {})
        dag = partial_kwargs.pop("dag")
        task_group = partial_kwargs.pop("task_group")

        operator = MappedOperator(
            operator_class=self.operator_class,
            mapped_kwargs=mapped_kwargs,
            partial_kwargs=partial_kwargs,
            task_id=task_id,
            params=params,
            deps=MappedOperator.deps_for(self.operator_class),
            operator_extra_links=self.operator_class.operator_extra_links,
            template_ext=self.operator_class.template_ext,
            template_fields=self.operator_class.template_fields,
            is_dummy=issubclass(self.operator_class, DummyOperator),
            task_module=self.operator_class.__module__,
            task_type=self.operator_class.__name__,
            dag=dag,
            task_group=task_group,
        )
        self.__dict__["__map_called"] = True
        return operator


@attr.define(kw_only=True)
class MappedOperator(AbstractOperator):
    """Object representing a mapped operator in a DAG."""

    operator_class: Union[Type["BaseOperator"], str]
    mapped_kwargs: Dict[str, Any]
    partial_kwargs: Dict[str, Any]

    # Needed for serialization.
    task_id: str
    params: Union[dict, ParamsDict]
    deps: FrozenSet[BaseTIDep]
    operator_extra_links: Collection["BaseOperatorLink"]
    template_ext: Collection[str]
    template_fields: Collection[str]
    _is_dummy: bool
    _task_module: str
    _task_type: str

    # These need extra work on init time.
    dag: Optional["DAG"]
    task_group: Optional[TaskGroup]
    upstream_task_ids: Set[str] = attr.ib(factory=set, init=False)
    downstream_task_ids: Set[str] = attr.ib(factory=set, init=False)

    def __attrs_post_init__(self):
        prevent_duplicates(self.partial_kwargs, self.mapped_kwargs, fail_reason="mapping already partial")
        self._validate_argument_count()
        if self.task_group:
            self.task_group.add(self)

    @classmethod
    @cache
    def get_serialized_fields(cls):
        return frozenset(attr.fields_dict(cls)) - {
            "dag",
            "deps",
            "task_group",
            "upstream_task_ids",
        }

    @staticmethod
    @cache
    def deps_for(operator_class: Type["BaseOperator"]) -> FrozenSet[BaseTIDep]:
        return operator_class.deps | {MappedTaskIsExpanded()}

    def _validate_argument_count(self) -> None:
        """Validate mapping arguments by unmapping with mocked values.

        This ensures the user passed enough arguments in the DAG definition for
        the operator to work in the task runner. This does not guarantee the
        arguments are *valid* (that depends on the actual mapping values), but
        makes sure there are *enough* of them.
        """
        if isinstance(self.operator_class, str):
            return  # No need to validate deserialized operator.
        mapped_kwargs = {k: unittest.mock.Mock() for k in self.mapped_kwargs}
        self.operator_class(
            dag=None,  # Intentionally omitting so this doesn't get added.
            task_group=None,  # Intentionally omitting so this doesn't get added.
            **self.partial_kwargs,
            **mapped_kwargs,
        )

    @property
    def task_type(self) -> str:
        """Implementing Operator."""
        return self._task_type

    @property
    def inherits_from_dummy_operator(self) -> bool:
        """Implementing Operator."""
        return self._is_dummy

    @property
    def roots(self) -> Sequence[AbstractOperator]:
        """Implementing DAGNode."""
        return [self]

    @property
    def leaves(self) -> Sequence[AbstractOperator]:
        """Implementing DAGNode."""
        return [self]

    def get_dag(self) -> Optional["DAG"]:
        """Implementing Operator."""
        return self.dag

    def serialize_for_task_group(self) -> Tuple[DagAttributeTypes, Any]:
        """Implementing DAGNode."""
        return DagAttributeTypes.OP, self.task_id

    def create_unmapped_operator(self) -> BaseOperator:
        assert not isinstance(self.operator_class, str)
        return self.operator_class(
            dag=self.dag,
            task_id=self.task_id,
            **self.partial_kwargs,
            **self.mapped_kwargs,
        )

    def unmap(self) -> BaseOperator:
        """Get the "normal" Operator after applying the current mapping"""
        dag = self.dag
        if not dag:
            raise RuntimeError("Cannot unmap a task without a DAG")
        dag._remove_task(self.task_id)
        return self.create_unmapped_operator()

    def expand_mapped_task(
        self,
        upstream_ti: "TaskInstance",
        session: Session = NEW_SESSION,
    ) -> Sequence["TaskInstance"]:
        """Create the mapped task instances for mapped task.

        :return: The mapped task instances, ascendingly ordered by map index.
        """
        # TODO: support having multiuple mapped upstreams?
        from airflow.models.taskinstance import TaskInstance
        from airflow.models.taskmap import TaskMap
        from airflow.settings import task_instance_mutation_hook

        task_map_info_length: Optional[int] = (
            session.query(TaskMap.length)
            .filter_by(
                dag_id=upstream_ti.dag_id,
                task_id=upstream_ti.task_id,
                run_id=upstream_ti.run_id,
                map_index=upstream_ti.map_index,
            )
            .scalar()
        )
        if task_map_info_length is None:
            # TODO: What would lead to this? How can this be better handled?
            raise RuntimeError("mapped operator cannot be expanded; upstream not found")

        state = None
        unmapped_ti: Optional[TaskInstance] = (
            session.query(TaskInstance)
            .filter(
                TaskInstance.dag_id == upstream_ti.dag_id,
                TaskInstance.run_id == upstream_ti.run_id,
                TaskInstance.task_id == self.task_id,
                TaskInstance.map_index == -1,
                or_(TaskInstance.state.in_(State.unfinished), TaskInstance.state.is_(None)),
            )
            .one_or_none()
        )

        ret: List[TaskInstance] = []

        if unmapped_ti:
            # The unmapped task instance still exists and is unfinished, i.e. we
            # haven't tried to run it before.
            if task_map_info_length < 1:
                # If the upstream maps this to a zero-length value, simply marked the
                # unmapped task instance as SKIPPED (if needed).
                self.log.info("Marking %s as SKIPPED since the map has 0 values to expand", unmapped_ti)
                unmapped_ti.state = TaskInstanceState.SKIPPED
                session.flush()
                return ret
            # Otherwise convert this into the first mapped index, and create
            # TaskInstance for other indexes.
            unmapped_ti.map_index = 0
            state = unmapped_ti.state
            self.log.debug("Updated in place to become %s", unmapped_ti)
            ret.append(unmapped_ti)
            indexes_to_map = range(1, task_map_info_length)
        else:
            # Only create "missing" ones.
            current_max_mapping = (
                session.query(func.max(TaskInstance.map_index))
                .filter(
                    TaskInstance.dag_id == upstream_ti.dag_id,
                    TaskInstance.task_id == self.task_id,
                    TaskInstance.run_id == upstream_ti.run_id,
                )
                .scalar()
            )
            indexes_to_map = range(current_max_mapping + 1, task_map_info_length)

        for index in indexes_to_map:
            # TODO: Make more efficient with bulk_insert_mappings/bulk_save_mappings.
            # TODO: Change `TaskInstance` ctor to take Operator, not BaseOperator
            ti = TaskInstance(self, run_id=upstream_ti.run_id, map_index=index, state=state)  # type: ignore
            self.log.debug("Expanding TIs upserted %s", ti)
            task_instance_mutation_hook(ti)
            ret.append(session.merge(ti))

        # Set to "REMOVED" any (old) TaskInstances with map indices greater
        # than the current map value
        session.query(TaskInstance).filter(
            TaskInstance.dag_id == upstream_ti.dag_id,
            TaskInstance.task_id == self.task_id,
            TaskInstance.run_id == upstream_ti.run_id,
            TaskInstance.map_index >= task_map_info_length,
        ).update({TaskInstance.state: TaskInstanceState.REMOVED})

        session.flush()

        return ret
