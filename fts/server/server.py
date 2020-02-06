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

import grpc
from fts.service import FastTextService
from fts.protos import service_pb2_grpc
from fts.service.exceptions import map_exceptions_grpc


class FastTextServicer(service_pb2_grpc.FastTextServicer):
    def __init__(self):
        self._fasttext_service = FastTextService()

    @map_exceptions_grpc
    def Predict(self, request, context):
        return self._fasttext_service.predict(request)

    @map_exceptions_grpc
    def GetLoadedModels(self, request, context):
        return self._fasttext_service.get_loaded_models()

    @map_exceptions_grpc
    def GetModelStatus(self, request, context):
        return self._fasttext_service.get_model_status(request)

    @map_exceptions_grpc
    def LoadModels(self, request, context):
        return self._fasttext_service.load_models(request)

    @map_exceptions_grpc
    def ReloadConfigModels(self, request, context):
        return self._fasttext_service.load_models_in_config_file()

    @map_exceptions_grpc
    def GetWordsVectors(self, request, context):
        return self._fasttext_service.get_words_vectors(request)
