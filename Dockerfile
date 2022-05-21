FROM python:3.10.4-slim-buster

LABEL maintainer="Eliam LOTONGA" email="contact@eliam-lotonga.fr"

EXPOSE 80

ENV APP_EXPOSED_PORT=80

RUN useradd --create-home appuser

USER appuser

ENV PATH="/home/appuser/.local/bin:${PATH}"

WORKDIR /home/appuser

COPY --chown=appuser:appuser ./requirements/common.txt .

RUN pip install --upgrade pip

RUN pip install --user --no-cache-dir --no-input -r common.txt

COPY --chown=appuser:appuser . .

RUN rm -rf requirements

CMD [ "python", "main.py" ]