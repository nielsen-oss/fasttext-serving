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
from pathlib import Path
from shutil import copytree, rmtree
from test.test_utils import FastTextServingTest

import grpc
import yaml
from fts.protos import model_pb2, service_pb2
from fts.utils.config import get_config


class TestModelLoading(FastTextServingTest):
    def test_loaded_models(self):

        # Get loaded models
        response = self.stub.GetLoadedModels(service_pb2.LoadedModelsRequest())
        loaded_models = [model.name for model in response.models]

        # Check that only bad models weren't loaded
        configured_models = [model["name"] for model in get_config()["models"]]
        for model in configured_models:
            if model not in loaded_models:
                self.assertIn(model, self.BAD_MODELS)
            else:
                self.assertNotIn(model, self.BAD_MODELS)

    def test_missing_models(self):
        try:
            self.stub.LoadModels(service_pb2.LoadModelsRequest())
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.INVALID_ARGUMENT)

    def test_empty_models(self):
        try:
            self.stub.LoadModels(service_pb2.LoadModelsRequest(models=()))
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.INVALID_ARGUMENT)

    def test_missing_model_path(self):
        request = service_pb2.LoadModelsRequest(
            models=(model_pb2.ModelSpec(name="headers"),)
        )
        response = self.stub.LoadModels(request)
        self.assertFalse(response.success)

    def test_missing_model_name(self):
        request = service_pb2.LoadModelsRequest(
            models=(model_pb2.ModelSpec(base_path="test/resources/headers"),)
        )
        response = self.stub.LoadModels(request)
        self.assertFalse(response.success)

    def test_bad_model_path(self):
        request = service_pb2.LoadModelsRequest(
            models=(
                model_pb2.ModelSpec(
                    name="foo", base_path="test/resources/models/not_existing"
                ),
            )
        )
        response = self.stub.LoadModels(request)
        self.assertFalse(response.success)

    def test_corrupt_model(self):
        model_spec = model_pb2.ModelSpec(
            name="corrupt", base_path="test/resources/models/corrupt"
        )
        request = service_pb2.LoadModelsRequest(models=(model_spec,))
        response = self.stub.LoadModels(request)
        self.assertFalse(response.success)

        # Check model's state is FAILED
        request = service_pb2.ModelStatusRequest(model=model_spec)
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "FAILED"
        )

    def test_correct(self):
        self.replace_corrupt_and_heavy_models()
        request = service_pb2.LoadModelsRequest(
            models=(
                model_pb2.ModelSpec(
                    name="corrupt", base_path="test/resources/models/corrupt"
                ),
                model_pb2.ModelSpec(
                    name="heavy", base_path="test/resources/models/heavy"
                ),
            )
        )
        response = self.stub.LoadModels(request)
        self.assertTrue(response.success)

        # Check both models' state is LOADED
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="corrupt")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="heavy")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        self.revert_model_changes()

    def test_highest_version(self):
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="correct")
        )
        previous_response = self.stub.GetModelStatus(request)
        self.assertEqual(previous_response.status.version, 1)
        copytree((self.CORRECT_MODEL_PATH / "1"), (self.CORRECT_MODEL_PATH / "2"))
        self.stub.ReloadConfigModels(service_pb2.ReloadModelsRequest())
        later_response = self.stub.GetModelStatus(request)
        self.assertEqual(later_response.status.version, 2)
        rmtree(self.CORRECT_MODEL_PATH / "2")

    def test_reload_models_in_config_file(self):

        # Replace heavy and corrupt model and reload them
        self.replace_corrupt_and_heavy_models()
        response = self.stub.ReloadConfigModels(service_pb2.ReloadModelsRequest())

        # Get loaded models
        response = self.stub.GetLoadedModels(service_pb2.LoadedModelsRequest())
        loaded_models = [model.name for model in response.models]

        # Check that only bad path model wasn't loaded
        configured_models = [model["name"] for model in get_config()["models"]]
        for model in configured_models:
            if model not in loaded_models:
                self.assertEqual(model, "bad_path")

        # Check haeavy and corrupt model state is LOADED
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="corrupt")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="heavy")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )
        self.revert_model_changes()

    def test_reloading_new_model(self):

        # Configure a new model
        config_path = os.environ["SERVICE_CONFIG_PATH"]
        with open(config_path, "r+") as f:
            config = yaml.load(f.read())
            config["models"].append({"base_path": "new", "name": "new"})
            yaml.dump(config, f)

        # Make the new model available and reload models
        self.duplicate_correct_model()

        # Check that the new model is loaded
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="new")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )

        # Revert changes
        self.revert_config_changes()
        self.revert_model_changes()


if __name__ == "__main__":
    unittest.main()
