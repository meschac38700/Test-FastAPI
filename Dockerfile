FROM python:3.10-alpine

LABEL maintainer="Eliam LOTONGA" email="contact@eliam-lotonga.fr"

RUN addgroup -S appgroup && adduser -S appuser -G appgroup 

ARG workDir=/app/src venv=/app/src/venv

ENV PATH="/home/appuser/.local/bin:${PATH}" APP_SRC=$workDir VENV=$venv

EXPOSE ${APP_PORT:-80}

RUN mkdir -p $workDir && chown -R appuser:appgroup $workDir

WORKDIR $workDir

USER appuser

COPY --chown=appuser:appgroup ./requirements .

RUN python -m venv $venv &&\
  source $venv/bin/activate &&\
  pip install --upgrade pip &&\
  pip install -r ./common.txt

COPY --chown=appuser:appgroup . .

RUN rm -rf common.txt requirements && chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]