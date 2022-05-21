# Get started Python FastAPI

[![codecov](https://codecov.io/gh/meschac38700/Test-FastAPI/branch/master/graph/badge.svg?token=iffvr8Fmg5)](https://codecov.io/gh/meschac38700/Test-FastAPI)
[![Workflow](https://github.com/meschac38700/Test-FastAPI/actions/workflows/workflow.yml/badge.svg?branch=master)](https://github.com/meschac38700/Test-FastAPI/actions/workflows/workflow.yml)
[![Lint](https://github.com/meschac38700/Test-FastAPI/actions/workflows/auto-format.yaml/badge.svg)](https://github.com/meschac38700/Test-FastAPI/actions/workflows/auto-format.yaml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Pypi](https://img.shields.io/pypi/v/pip.svg)](https://pypi.org/project/pip/)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![CC-0 license](https://img.shields.io/badge/License-CC--0-blue.svg)](https://github.com/meschac38700/Test-FastAPI/blob/master/LICENSE)

## Client apps

- [App-1](https://github.com/meschac38700/fastAPI-client-side)
- [App-2](https://github.com/meschac38700/comment-design)

## Python versions

### >= 3.9

## Install with docker-compose

Then run:

```bash
docker-compose -f docker-compose.yml up
```

The app running on http://127.0.0.1:8000/

## Manual installation without docker

##### requirements:
    - Postgresql
    - python

Note that, you can create a virtual environment
if you don't want to install requirements in your host machine

For that run the following command *depending on your system*:

```bash
python -m venv {venv-name}
```

activate this virtual environment

Linux or Mac

```bash
source {venv-name}/bin/activate
```

Windows

```bash
./{venv-name}/Scripts/activate
```

### Install requirements

Upgrade `pip`

```bash
pip install --upgrade pip
```

install application requirements

```bash
pip install -r  requirements/common.txt
```

install dev requirements (useful to run tests)

```bash
pip install -r requirements/dev.txt
```

### Database

Connect to your postgres BD using `psql`

```bash
psql -U postgres -p 5432 -h localhost
```

Then create DB `fastapidb`

```bash
CREATE DATABASE fastapidb;
```

Then edit correctly `TORTOISE_ORM` variable in the [settings.py](https://github.com/meschac38700/Test-FastAPI/blob/master/app/api/api_v1/settings.py#L5) file.

We are using [Aerich](https://github.com/tortoise/aerich) as database migrations tool.
Init database by running the following aerich command:

```bash
aerich init-db
```

## Run the app

```bash
python main.py
```

The app running on [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

## Fake Data

To load some fake data, go to [http://127.0.0.1:8000/data](http://127.0.0.1:8000/data)
which will load fake data.

## Run all the tests

from root folder`(Test-FastAPI/)` run:

```bash
pytest
```

### Contributors

Made by:

![image](https://contrib.rocks/image?repo=meschac38700/Test-FastAPI)
