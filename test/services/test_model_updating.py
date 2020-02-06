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

import time
from pathlib import Path
from shutil import copytree, rmtree

import grpc

from fts.protos import model_pb2, service_pb2
from fts.utils.config import get_config
from test.test_utils import FastTextServingTest


class TestModelUpdating(FastTextServingTest):
    def test_update_loaded_model(self):
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="correct")
        )
        previous_response = self.stub.GetModelStatus(request)
        self.assertEqual(previous_response.status.version, 1)
        copytree((self.CORRECT_MODEL_PATH / "1"), (self.CORRECT_MODEL_PATH / "2"))
        time.sleep(3)
        later_response = self.stub.GetModelStatus(request)
        self.assertEqual(later_response.status.version, 2)
        rmtree(self.CORRECT_MODEL_PATH / "2")

    def test_update_available_model(self):
        copytree((self.CORRECT_MODEL_PATH / "1"), (self.HEAVY_MODEL_PATH / "2"))
        time.sleep(3)
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="heavy")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        rmtree(self.HEAVY_MODEL_PATH / "2")

    def test_update_bad_path_model(self):
        copytree(self.CORRECT_MODEL_PATH, self.BAD_PATH)
        time.sleep(3)
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="bad_path")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        rmtree(self.BAD_PATH)

    def test_update_corrupt_model(self):
        copytree((self.CORRECT_MODEL_PATH / "1"), (self.CORRUPT_MODEL_PATH / "2"))
        time.sleep(3)
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="corrupt")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        rmtree(self.CORRUPT_MODEL_PATH / "2")
