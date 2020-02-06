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
from multiprocessing.pool import ThreadPool
from test.test_utils import FastTextServingTest
from threading import Thread
from fts.protos import service_pb2


class TestPredict(FastTextServingTest):
    @classmethod
    def setUpClass(self):
        super().setUpClass()
        super().replace_corrupt_and_heavy_models()

    def test_one_word(self):
        request = service_pb2.PredictRequest(model_name="correct", batch=["price"], k=2)
        response = self.stub.Predict(request, None)
        self.assertTrue(len(response.predictions) == 1)
        self.assertTrue(len(response.predictions[0].labels) == 2)
        self.assertTrue(len(response.predictions[0].scores) == 2)
        self.assertTrue(response.model.name == request.model_name)

    def test_various_words(self):
        request = service_pb2.PredictRequest(
            model_name="correct", batch=["total price", "quantity", "anything"], k=2
        )
        response = self.stub.Predict(request, None)
        self.assertTrue(len(response.predictions) == 3)
        self.assertTrue(len(response.predictions[0].labels) == 2)
        self.assertTrue(len(response.predictions[0].scores) == 2)
        self.assertTrue(response.model.name == request.model_name)

    def test_missing_model(self):
        request = service_pb2.PredictRequest(batch=["price"])
        try:
            self.stub.Predict(request, None)
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.INVALID_ARGUMENT)

    def test_missing_words(self):
        request = service_pb2.PredictRequest(model_name="foo")
        try:
            self.stub.Predict(request, None)
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.INVALID_ARGUMENT)

    def test_not_loaded_model(self):
        request = service_pb2.PredictRequest(model_name="folder", batch=["price"])
        try:
            self.stub.Predict(request, None)
        except grpc.RpcError as error:
            self.assertTrue(error._state.code == grpc.StatusCode.FAILED_PRECONDITION)

    def test_concurrency_same_model(self):

        # Get correct vector
        correct_word = self.predict(("correct"))

        # Check if we get the correct vectors concurrently
        correct = True
        with ThreadPool(processes=4) as pool:
            results = [
                pool.apply_async(self.predict, ("correct",)) for i in range(1000)
            ]
            for result in results:
                if result.get() != correct_word:
                    correct = False
                    break
        self.assertTrue(correct)

    def test_concurrency_different_models(self):

        # Get correct vectors
        correct_word = self.predict(("correct"))
        corrupt_word = self.predict(("corrupt"))
        heavy_word = self.predict(("heavy"))

        # Check if we get the correct vectors concurrently
        correct = True
        with ThreadPool(processes=4) as pool:
            results = [
                pool.apply_async(self.predict, ("correct", "corrupt", "heavy",))
                for i in range(1000)
            ]
            for result in results:
                res = result.get()
                if result.get() != [correct_word[0], corrupt_word[0], heavy_word[0]]:
                    correct = False
                    break
        self.assertTrue(correct)

    def predict(self, *models):
        response = []
        for model in models:
            request = service_pb2.PredictRequest(model_name=model, batch=["price"], k=1)
            response += self.stub.GetWordsVectors(request, None).vectors
        return response


if __name__ == "__main__":
    unittest.main()
