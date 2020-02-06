# Copyright 2020 Nielsen Global Connect.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time
from concurrent import futures

import grpc
import grpc_health.v1.health_pb2 as health_pb2
import grpc_health.v1.health_pb2_grpc as health_pb2_grpc
from fts.protos import service_pb2_grpc
from fts.server import FastTextServicer
from fts.utils.config import get_config
from fts.utils.logger import get_logger
from grpc_health.v1.health import HealthServicer

_ONE_DAY_IN_SECONDS = 60 * 60 * 24


def serve():
    logger = get_logger()
    logger.info("FastText server starting ...")

    # Read gRPC options
    config = get_config()
    grpc_port = config["grpc"].get("port", 50051)
    grpc_max_workers = config["grpc"].get("max_workers", 2)
    grpc_maximum_concurrent_rpcs = config["grpc"].get("maximum_concurrent_rpcs", 25)
    logger.info("Concurrent workers: {}".format(grpc_max_workers))
    logger.info("gRPC queue size: {}".format(grpc_maximum_concurrent_rpcs))

    # Read gRPC channel options
    grpc_options = []
    for option in config["grpc"].get("channel_options", {}).items():
        logger.info("gRPC channel option: {}".format(option))
        grpc_options.append(option)

    # Create server
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=grpc_max_workers),
        maximum_concurrent_rpcs=grpc_maximum_concurrent_rpcs,
        options=grpc_options,
    )

    # Add servicers
    servicer = FastTextServicer()
    service_pb2_grpc.add_FastTextServicer_to_server(servicer, server)
    health_servicer = HealthServicer()
    health_pb2_grpc.add_HealthServicer_to_server(health_servicer, server)

    # Run server
    address = "[::]:{}".format(grpc_port)
    server.add_insecure_port(address)
    server.start()
    logger.info("Listening incoming connections at {}".format(address))

    # Mark the server as running using gRPC health check protocol
    serving_status = health_pb2._HEALTHCHECKRESPONSE_SERVINGSTATUS
    status_code = serving_status.values_by_name["SERVING"].number
    health_servicer.set("", status_code)
    logger.info("gRPC health check protocol: {}".format(status_code))

    try:
        while True:
            time.sleep(_ONE_DAY_IN_SECONDS)
    except KeyboardInterrupt:
        server.stop(0)
        servicer = None


if __name__ == "__main__":
    serve()
