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
import grpc
import time
import unittest
from concurrent import futures
from pathlib import Path
from threading import Thread
from shutil import copytree, rmtree

from fts.protos import service_pb2, service_pb2_grpc
from fts.server import FastTextServicer


def _start_grpc_server(cls):
    servicer = FastTextServicer()
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        maximum_concurrent_rpcs=100,
        options=(
            ("grpc.max_send_message_length", 59430547),
            ("grpc.max_receive_message_length", 59430547),
        ),
    )
    service_pb2_grpc.add_FastTextServicer_to_server(servicer, server)
    server.add_insecure_port("[::]:50051")
    server.start()
    cls._server_running = True
    try:
        while not cls._stop_server:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop(0)
    server.stop(0)
    cls._server_running = False


class FastTextServingTest(unittest.TestCase):

    MODELS_DIR = Path("test/resources/models")
    MODELS_BACKUP_DIR = Path("test/resources/models-backup")
    CORRECT_MODEL_PATH = MODELS_DIR / "correct"
    HEAVY_MODEL_PATH = MODELS_DIR / "heavy"
    CORRUPT_MODEL_PATH = MODELS_DIR / "corrupt"
    BAD_PATH = MODELS_DIR / "bad_path"
    BAD_MODELS = ["heavy", "corrupt", "bad_path"]

    @classmethod
    def setUpClass(cls):
        cls._server_running = False
        cls._stop_server = False
        cls._server_thread = Thread(target=_start_grpc_server, args=(cls,))
        cls._server_thread.start()
        while not cls._server_running:
            time.sleep(0.25)
        cls._channel = grpc.insecure_channel("localhost:50051")
        cls.stub = service_pb2_grpc.FastTextStub(cls._channel)
        cls.backup_model_changes()

    @classmethod
    def tearDownClass(cls):
        cls.revert_model_changes()
        cls._stop_server = True
        cls._server_thread.join()

    @classmethod
    def replace_corrupt_and_heavy_models(cls):
        cls.backup_model_changes()
        rmtree(cls.CORRUPT_MODEL_PATH)
        copytree(cls.CORRECT_MODEL_PATH, cls.CORRUPT_MODEL_PATH)
        rmtree(cls.HEAVY_MODEL_PATH)
        copytree(cls.CORRECT_MODEL_PATH, cls.HEAVY_MODEL_PATH)
        cls.stub.ReloadConfigModels(service_pb2.ReloadModelsRequest())

    @classmethod
    def revert_model_changes(cls):
        rmtree(cls.MODELS_DIR)
        copytree(cls.MODELS_BACKUP_DIR, cls.MODELS_DIR)
        cls.stub.ReloadConfigModels(service_pb2.ReloadModelsRequest())

    @classmethod
    def backup_model_changes(cls):
        rmtree(cls.MODELS_BACKUP_DIR, ignore_errors=True)
        copytree(cls.MODELS_DIR, cls.MODELS_BACKUP_DIR)
