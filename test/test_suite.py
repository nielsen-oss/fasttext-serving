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
import unittest

path = os.path.abspath(__file__ + "/../")
dir_path = os.path.dirname(path)
sys.path.insert(0, dir_path)

os.environ["SERVICE_CONFIG_PATH"] = "test/resources/test-config.yaml"

from test.services.test_model_loading import TestModelLoading
from test.services.test_predict import TestPredict
from test.services.test_get_word_vectors import TestWordVectors
from test.services.test_model_updating import TestModelUpdating
from test.services.test_get_model_status import TestModelStatus


def suite():
    test_list = [
        TestModelStatus,
        TestWordVectors,
        TestPredict,
        TestModelLoading,
        TestModelUpdating,
    ]

    test_load = unittest.TestLoader()
    case_list = []
    for test_case in test_list:
        test_suite = test_load.loadTestsFromTestCase(test_case)
        case_list.append(test_suite)

    return unittest.TestSuite(case_list)


def run_tests():
    runner = unittest.TextTestRunner(verbosity=2)
    test_suite = suite()
    return runner.run(test_suite)


if __name__ == "__main__":
    r = run_tests()
    if len(r.errors) > 0 or len(r.failures) > 0:
        exit(-1)
    else:
        exit(0)
