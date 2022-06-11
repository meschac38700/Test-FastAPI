#!/bin/sh

cd ${APP_SRC}
source ${VENV}/bin/activate
aerich init -t app.api.api_v1.settings.TORTOISE_ORM
aerich init-db
python main.py