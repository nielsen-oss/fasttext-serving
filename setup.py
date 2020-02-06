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
from os.path import isdir, join
from pathlib import Path

from grpc_tools import protoc
from setuptools import find_packages, setup
from setuptools.command.install import install


class BuildProtos(install):
    """
    Fix relative imports
    https://github.com/protocolbuffers/protobuf/issues/1491
    """

    def run(self):
        Path("fts/protos/").mkdir()
        protoc.main(
            [
                "protoc",
                "-I",
                "protos",
                "--python_out=fts/protos",
                "--grpc_python_out=fts/protos",
                "model.proto",
                "service.proto",
            ]
        )

        Path("fts/protos/__init__.py").touch()
        with open("fts/protos/__init__.py", "w") as f:
            f.writelines(
                [
                    "import sys\n",
                    "from pathlib import Path\n",
                    "sys.path.append(str(Path(__file__).parent))",
                ]
            )


setup(
    name="fasttext-serving",
    description="TODO",
    url="TODO",
    version="1.0.0",
    cmdclass={"install": BuildProtos,},
    packages=find_packages(include=["fts*"]),
)
