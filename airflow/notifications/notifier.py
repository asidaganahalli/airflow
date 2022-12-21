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

from abc import abstractmethod
from typing import TYPE_CHECKING, Sequence

import jinja2

from airflow.template.templater import Templater
from airflow.utils.context import Context, context_merge

if TYPE_CHECKING:
    from airflow import DAG


class Notifier(Templater):
    """
    Base Notifier class for sending notifications

    :param message: The message to send

    The message or template_file can be used to send a notification. If both are set, the message
    will be used.
    """

    template_fields: Sequence[str] = ("message",)
    template_ext: Sequence[str] = (".txt",)

    def __init__(
        self,
        message: str | None = "This is a default message",
    ):
        super().__init__()
        self.message = message
        self.resolve_template_files()

    def _update_context(self, context: Context) -> Context:
        """
        Add additional context to the context

        :param context: The airflow context
        """
        additional_context = {}
        for field in self.template_fields:
            additional_context[field] = getattr(self, field)
        context_merge(context, additional_context)
        return context

    def _render(self, template, context, dag: DAG | None = None):
        dag = context["dag"] if dag is None else dag
        return super()._render(template, context, dag)

    def render_template_fields(
        self,
        context: Context,
        jinja_env: jinja2.Environment | None = None,
    ) -> None:
        """Template all attributes listed in *self.template_fields*.

        This mutates the attributes in-place and is irreversible.

        :param context: Context dict with values to apply on content.
        :param jinja_env: Jinja environment to use for rendering.
        """
        context = self._update_context(context)
        dag = context["dag"]
        if not jinja_env:
            jinja_env = self.get_template_env(dag=dag)
        self._do_render_template_fields(self, self.template_fields, context, jinja_env, set())

    @abstractmethod
    def notify(self, context: Context) -> None:
        """
        Sends a notification

        subclasses should always call super().notify(context) first to ensure
        that the template is rendered with the context.

        :param context: The airflow context
        """
        self.render_template_fields(context)

    def __call__(self, context: Context) -> None:
        """
        Send a notification

        :param context: The airflow context
        """
        try:
            self.notify(context)
        except Exception as e:
            self.log.exception("Failed to send notification: %s", e)
