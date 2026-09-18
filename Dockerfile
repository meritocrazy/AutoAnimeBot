FROM python:3.12-slim-bookworm

WORKDIR /usr/src/app

RUN apt-get -qq update && apt-get -qq install -y git wget pv jq python3-dev mediainfo gcc aria2 libsm6 libxext6 libfontconfig1 libxrender1 libgl1-mesa-glx ffmpeg && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /usr/src/app
USER appuser
COPY --chown=appuser:appuser . .
RUN pip3 install --no-cache-dir -r requirements.txt

CMD ["bash","run.sh"]