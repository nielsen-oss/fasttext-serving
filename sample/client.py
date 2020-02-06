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

from fts.protos import service_pb2, service_pb2_grpc

if __name__ == "__main__":

    # Generate GRPC stub
    channel = grpc.insecure_channel("localhost:50051")
    stub = service_pb2_grpc.FastTextStub(channel)

    # Predict
    request = service_pb2.PredictRequest(
        model_name="headers", batch=["one", "two", "three"], k=1
    )
    response = stub.Predict(request)
    print(stub.Predict(request).predictions)
