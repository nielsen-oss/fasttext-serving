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
from functools import wraps
from google.protobuf.empty_pb2 import Empty


class ModelNotLoadedException(Exception):
    """
    The model has not been loaded in memory
    """
    pass


class MissingArgumentException(Exception):
    """
    There is an error in one of the arguments in the request
    """
    pass


class FastTextException(Exception):
    """
    Internal exception captured from fastText
    """
    pass


EXC_MAPPING = {
    ModelNotLoadedException: grpc.StatusCode.FAILED_PRECONDITION,
    MissingArgumentException: grpc.StatusCode.INVALID_ARGUMENT,
    FastTextException: grpc.StatusCode.UNKNOWN,
}


def map_exceptions_grpc(function):
    def wrapper(*args, **kwargs):
        context = args[2]
        try:
            return function(*args, **kwargs)
        except Exception as ex:
            for exc_key in EXC_MAPPING:
                if isinstance(ex, exc_key):
                    context.set_code(EXC_MAPPING[exc_key])
                    context.set_details(str(ex))
            return Empty()

    return wrapper
