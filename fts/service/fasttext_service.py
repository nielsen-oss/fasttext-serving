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
import yaml
import time
import fasttext
from collections import namedtuple
from pathlib import Path

from fts.service.exceptions import (
    FastTextException,
    MissingArgumentException,
    ModelNotLoadedException,
)
from fts.protos import model_pb2, service_pb2
from fts.utils.config import get_config
from fts.utils.logger import get_logger
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

Model = namedtuple("Model", "pb_model ft_model size state")
config = get_config()
logger = get_logger()


class ModelUpdateHandler(FileSystemEventHandler):
    def __init__(self, fasttext_service):
        self._fasttext_service = fasttext_service

    def on_created(self, event):
        self._fasttext_service._handle_file_update(Path(event.src_path))


class FastTextService(object):
    def __init__(self):

        self.load_models_in_config_file()

        # Start watchdog
        self._observer = Observer()
        self._observer.schedule(
            ModelUpdateHandler(self), path=config["models_path"], recursive=True
        )
        self._observer.start()

    def load_models_in_config_file(self) -> service_pb2.LoadModelsResponse:
        self._memory_factor = float(config["memory"]["memory_factor"])
        self._available_memory = int(config["memory"]["available_memory"])
        self._configured_models = self._get_models_from_config()
        self._models = {}

        success = True
        for base_path, model_name in self._configured_models.items():
            if success:
                success = self._load_model(model_name, Path(base_path))
            else:
                self._load_model(model_name, Path(base_path))

        return service_pb2.LoadModelsResponse(success=success)

    def _load_model(self, name: str, base_path: Path):
        path = self._get_latest_version_path(base_path)
        if path is not None:

            # Check if model was already loaded
            if (
                name in self._models
                and self._models[name].state == model_pb2.ModelStatus.LOADED
            ):
                old_size = self._models[name].size
            else:
                old_size = 0

            # Load model
            size = path.stat().st_size * self._memory_factor
            if self._available_memory > (size - old_size):
                try:
                    self._models[name] = Model(
                        model_pb2.ModelSpec(
                            name=name,
                            base_path=str(base_path),
                            version=int(path.parent.name),
                        ),
                        fasttext.load_model(str(path)),
                        size,
                        model_pb2.ModelStatus.LOADED,
                    )
                    self._available_memory -= size - old_size
                    logger.info(f"Model {name} loaded from {path}")
                    return True
                except Exception as ex:
                    logger.warning(f"Error loading model {name} from {path}: {ex}")
                    self._models[name] = Model(
                        None, None, None, state=model_pb2.ModelStatus.FAILED
                    )
                    return False

            logger.warning(
                f"Not enough available memory to load model {name} from {path}"
            )
            self._models[name] = Model(
                None, None, None, state=model_pb2.ModelStatus.AVAILABLE
            )
            return False

        logger.warning(f"Not model available in {base_path}")
        return False

    def load_models(
        self, request: service_pb2.LoadModelsRequest
    ) -> service_pb2.LoadModelsResponse:
        # Check missing args
        if len(request.models) == 0:
            raise MissingArgumentException("Missing argument")

        success = True
        for model in request.models:
            # Check missing args
            if model.name == "" or model.base_path == "":
                logger.warning(f"Did not load model, missing argument")
                success = False
            else:
                if (
                    model.name not in self._models
                    or self._models[model.name].state != model_pb2.ModelStatus.LOADED
                ):
                    self._load_model(model.name, Path(model.base_path))
                success = self._models[model.name].state == model_pb2.ModelStatus.LOADED

        return service_pb2.LoadModelsResponse(success=success)

    def predict(
        self, request: service_pb2.PredictRequest
    ) -> service_pb2.PredictResponse:

        # Check args
        self._check_args(request)
        self._check_model(request.model_name)

        # Call FastText model
        try:
            labels, scores = self._models[request.model_name].ft_model.predict(
                text=list(request.batch), k=request.k
            )
        except Exception as ex:
            raise FastTextException(ex)

        # Generate response
        predictions = []
        for k_labels, k_scores in zip(labels, scores):
            prediction = model_pb2.Prediction(
                labels=[label.replace("__label__", "") for label in k_labels],
                scores=k_scores.astype(float),
            )
            predictions.append(prediction)

        return service_pb2.PredictResponse(
            model=self._models[request.model_name].pb_model, predictions=predictions
        )

    def get_loaded_models(self) -> service_pb2.LoadedModelsResponse:
        loaded_models = []
        for model in self._models.values():
            if model.state == model_pb2.ModelStatus.LOADED:
                loaded_models.append(model.pb_model)
        return service_pb2.LoadedModelsResponse(models=loaded_models)

    def get_model_status(
        self, request: service_pb2.ModelStatusRequest
    ) -> service_pb2.ModelStatusResponse:
        if request.model.name == "":
            raise MissingArgumentException("Missing argument model name")
        else:
            if request.model.name not in self._models:
                return service_pb2.ModelStatusResponse(
                    status=model_pb2.ModelStatus(state=model_pb2.ModelStatus.UNKWOWN)
                )
            if self._models[request.model.name].state == model_pb2.ModelStatus.LOADED:
                return service_pb2.ModelStatusResponse(
                    status=model_pb2.ModelStatus(
                        state=self._models[request.model.name].state,
                        version=self._models[request.model.name].pb_model.version,
                    )
                )
            return service_pb2.ModelStatusResponse(
                status=model_pb2.ModelStatus(
                    state=self._models[request.model.name].state
                )
            )

    def _handle_file_update(self, updated_path):
        if updated_path.is_file():
            base_path = updated_path.parent.parent
            if str(base_path) in self._configured_models:
                model_path = self._get_latest_version_path(base_path)
                if model_path is not None:
                    model_name = self._configured_models[str(base_path)]
                    logger.info(
                        f"Model {model_name}'s base_path {base_path} has been modified."
                    )

                    # Wait until model size hasn't changed for 1 second
                    while True:
                        prev_size = model_path.stat().st_size
                        time.sleep(1)
                        now_size = model_path.stat().st_size
                        if now_size == prev_size:
                            self._load_model(model_name, base_path)
                            break

    @staticmethod
    def _get_latest_version_path(base_path: Path) -> Path:
        if base_path.is_dir():

            # Get version directory with the highest name
            versions = [entry.name for entry in base_path.iterdir() if entry.is_dir()]
            if len(versions) == 0:
                return None
            latest_version_dir = base_path / max(versions)

            # Search for a .bin or .ftz file inside it
            files = list(latest_version_dir.glob("*.bin")) + list(
                latest_version_dir.glob("*.ftz")
            )
            if len(list(files)) == 1:
                return files[0]

        return None

    def get_words_vectors(
        self, request: service_pb2.VectorsRequest
    ) -> service_pb2.VectorsResponse:

        # Check args
        self._check_args(request)
        self._check_model(request.model_name)

        # Generate response
        try:
            vectors = []
            for word in request.batch:
                vectors.append(
                    model_pb2.WordVector(
                        element=list(
                            self._models[request.model_name].ft_model.get_word_vector(
                                word
                            )
                        )
                    )
                )
            response = service_pb2.VectorsResponse(
                model=self._models[request.model_name].pb_model, vectors=vectors
            )
        except Exception as ex:
            raise FastTextException(ex)
        return response

    def _check_model(self, model_name):
        if model_name not in self._models:
            raise ModelNotLoadedException(f"Unknown model {model_name}")
        if self._models[model_name].state != model_pb2.ModelStatus.LOADED:
            raise ModelNotLoadedException(f"Model {model_name} not loaded")

    @staticmethod
    def _check_args(request):
        if request.model_name is None or request.batch is None:
            raise MissingArgumentException("Missing argument")
        if request.model_name == "" or request.batch == []:
            raise MissingArgumentException("Missing argument")

    @staticmethod
    def _get_models_from_config():
        configured_models = {}
        for model in config["models"]:
            try:
                model_base_path = "/".join([config["models_path"], model["base_path"]])
            except:
                model_base_path = "/".join(
                    [config["models_path"], model["name"]]
                )  # Not model base path specified
            configured_models[model_base_path] = model["name"]
        return configured_models
