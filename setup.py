from setuptools import setup, find_packages

setup(
    name='dbt_opentelemetry',
    version='0.1',
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires='>=3.8',
    entry_points='''
        [console_scripts]
        dbt=dbt_opentelemetry.monkey_patching:main
    ''',
)
