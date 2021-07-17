"""This is where we do all the "monkey patching" to wrap the functions we want to trace in Open Telemetry code."""

import logging
import sys

import dbt.main

from dbt_opentelemetry.model_runner import ModelRunnerOpenTelemetry
from dbt_opentelemetry.run_task import RunTaskOpenTelemetry

# Logging init
logger = logging.getLogger(__name__)


def main():
    logger.info("Monkey patching dbt with dbt-opentelemetry..")
    dbt.task.run.ModelRunner = ModelRunnerOpenTelemetry
    dbt.task.run.RunTask = RunTaskOpenTelemetry
    dbt.main.main(sys.argv[1:])
