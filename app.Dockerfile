FROM  python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /xeneta-ratetask
COPY requirements.freeze.txt ./
RUN pip3 install --no-cache-dir -r requirements.freeze.txt

COPY ./ratetask ./
