FROM python:3.8.1-slim-buster

# Define the default application path
WORKDIR /usr/src/app

# Install Python dependencies
COPY requirements.txt requirements.txt
RUN apt-get update && \
    apt-get install -y g++ && \
    python -m pip install -U pip && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    apt-get remove -y g++ && \
    apt-get autoremove -y && \
    rm -rf /root/.cache && \
    rm -rf /var/lib/apt/lists/*

# Compile protos
COPY fts fts
COPY test test
COPY protos protos
COPY setup.py setup.py
RUN python setup.py install

# Run the service as a non-root user
COPY sample/config.yaml sample-config.yaml
ENV SERVICE_CONFIG_PATH /etc/fts/config.yaml
USER 1001
CMD ["python", "-O", "-m", "fts"]