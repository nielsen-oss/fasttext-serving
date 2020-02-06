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
from test.test_utils import FastTextServingTest
from fts.protos import model_pb2, service_pb2


class TestModelStatus(FastTextServingTest):
    def test_missing_name(self):
        try:
            request = model_pb2.ModelSpec()
            self.stub.GetModelStatus(request)
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.INVALID_ARGUMENT)

    def test_missing_name_and_version(self):
        try:
            request = model_pb2.ModelSpec(version=1)
            self.stub.GetModelStatus(request)
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.INVALID_ARGUMENT)

    def test_loaded(self):
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="correct")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "LOADED"
        )

    def test_unknown(self):
        request = service_pb2.ModelStatusRequest(model=model_pb2.ModelSpec(name="foo"))
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "UNKNOWN"
        )

    def test_failed(self):
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="corrupt")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "FAILED"
        )

    def test_available(self):
        request = service_pb2.ModelStatusRequest(
            model=model_pb2.ModelSpec(name="heavy")
        )
        response = self.stub.GetModelStatus(request)
        self.assertTrue(
            model_pb2.ModelStatus.ModelState.Name(response.status.state) == "AVAILABLE"
        )


if __name__ == "__main__":
    unittest.main()
