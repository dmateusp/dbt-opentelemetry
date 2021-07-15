# dbt-opentelemetry

WARNING: This is an experiment, do not depend on it in production, if it turned out to be useful it should be re-implemented in the core `dbt` project and not "monkey patched" into it.

An experiment of integrating [Open Telemetry](https://opentelemetry-python.readthedocs.io) and [dbt](https://www.getdbt.com/).

Can we re-use the concepts of tracing and distributed tracing to have better observability of our data pipelines? What are the challenges of applying concepts of Request tracing to Batch processes? This is what I am trying to figure out.

## Alternative

There is another solution to audit dbt runs: [dbt-event-logging](https://github.com/dbt-labs/dbt-event-logging). I think this solution has some drawbacks however:

* It writes to the Data Warehouse, so the audit can slow down the runs.
* It does not come with out of the box visualizations and alerting.
* It is specific to dbt, so if our pipeline workload is "distributed" across different systems like Airflow, dbt, Beam, internal services (like ML models), we need different strategies to see the "full picture".

## Solution

With the Open Telemetry API we can emit traces in all the components that make up our data pipeline, and plug-in "receivers" (tracing back-ends) to visualize and alert on these traces. This project uses [Jaeger tracing](https://www.jaegertracing.io/) as the backend because it is easy to provide in a [docker compose](https://docs.docker.com/compose/) environment. However, know that there are more back-ends compatible with Open Telemetry.

Here, I use the [Open Telemetry collector](https://github.com/open-telemetry/opentelemetry-collector) to simulate a production environment. An example production set up could include a dbt process running in a Kubernetes pod with an Open Telemetry collector agent running as a sidecar. The collector is [configured](./opentelemetry-collector-config.yaml) to "export" the traces to Jaeger and to a json file.

TODO: Add the "distributed" piece with an example.

## Notes

Open Tracing does not support "multiple parents" making it hard to represent a DAG. I made the _questionable_ decision of duplicating a Span for each parent it has. On Jaeger, it looks like a model/seed ran more than once, when in reality it just had multiple parents, but I find it more intuitive to be able to see the dependencies.

[This issue](https://github.com/apache/airflow/issues/12771) on the Airflow project sparked my interest in Open Telemetry for data pipelines. There is also this [RFC](https://github.com/open-telemetry/opentelemetry-specification/pull/1582) to define a "Job" trace in Open Telemetry.

## Getting started

This project contains a demo you can run on your laptop.

1. Install this project: `pip install .`. Use a virtual environment because this project "monkey patches" the dbt entrypoint, meaning it will change the behavior of calling `dbt` on the CLI.

2. Install the requirements: `pip install -r requirements.txt`.

3. Start the Postgres database, Jaeger tracing instance, and Open Telemetry collector: `docker compose up`.

4. Copy the following target to your dbt profiles `~/.dbt/profiles.yml`:

    ```yaml
    dbt-opentelemetry:
        type: postgres
        host: localhost
        user: dbt
        pass: dbt
        port: 5432
        dbname: dbt
        schema: dbt
        threads: 2
    ```

5. Run your dbt project, or run the test dbt project in this repository: `(cd tests/dbt-project; dbt run --target=dbt-opentelemetry)`.
