FROM python:3.10 AS build

ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

WORKDIR /app

RUN python -m pip --no-cache-dir install -U pip  \
    && pip install --no-cache-dir -U poetry

COPY . ./

RUN poetry build

FROM python:3.10

WORKDIR /app

COPY --from=0 /app/dist /app/dist

RUN python -m pip install -U pip \
    && pip install --no-cache-dir /app/dist/*.whl

EXPOSE 8000

ENTRYPOINT ["crawlerstack_proxypool"]
CMD ["api","-p","8000"]
