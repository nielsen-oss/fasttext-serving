# FastText Serving

FastText Serving is a simple and efficient serving system for [fastText](https://fasttext.cc) models. Inspired by TensorFlow Serving, it provides the missing piece in the microservice puzzle to connect your business logic with basic Natural Language Processing (NLP). The idea of this project is to provide an elegant and reusable implementation for managing several fastText models, allowing to run concurrent multi model predictions. The API of the service is based on gRPC to reduce network latency and deliver higher throughput. For instance, you can run millions of predictions in around one second using just a single CPU.

The service has been developed in Python, making use of Facebook's fastText library for running predictions over text pieces (words, sentences, paragraphs, etc.). The fastText API is used through the Python bindings provided in the official project. Clients of the service can boost their performance by sending multiple sentences grouped in batches within the same request as the fastText library is compiled as a binary.

Serving models are determined by reading the contents of a [configuration file](sample/config.yaml). These models are cached in memory depending on the amount of memory available and the size of the model. Every request is dispatched to the model specified in the body of that request. In addition, models are reloaded when a newer version is published or the file contents are changed in disk, thanks to the [watchdog](https://github.com/gorakhargosh/watchdog) library.

## Features

These are the most interesting features of this project:

- Concurrent management and serving of different models 
- Model versioning, allowing A/B test with concurrent requests to different versions
- Hot model serving, loading the new model as soon as a new version is detected in the storage
- Both bag of words and skip-gram models are supported
- gRPC API

## Quick Start

```bash
# Clone the repository
git clone https://github.com/nielsen-oss/fasttext-serving
cd fasttext-serving

# Build the Docker image
IMAGE_NAME=fasttext-serving
docker image build -t IMAGE_NAME .

# Start serving some example models
docker run -p 50051:50051 \
  -v ${PWD}/sample/models:/models \
  -v ${PWD}/sample/config.yaml:/etc/fts/config.yaml \
  -e SERVICE_CONFIG_PATH=/etc/fts/config.yaml \
  IMAGE_NAME 

# You can download pretrained models from fasttext webpage
# https://fasttext.cc/docs/en/supervised-models.html
# Do not forget to include the model in the models section of the config
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/dbpedia.ftz -P sample/models/dbpedia/1/

# Install requirements
pip3 install -r requirements.txt

# Compile protocol buffers (required by the client)
pip3 install .

# Make predictions using the example client
python3 sample/client.py
```

### API

The gRPC API exposes a set of methods for performing model management and predictions with fastText. More specifically, the service provides this functionalities:

  - Classify a sentence
  - Get the words vectors of a set of words
  - Get currently loaded models
  - Load a list of models
  - Reload the models in the configuration file
  - Get the status of a given model:
    - *UNKNOWN*: The model is not defined in the configuration file
    - *LOADED*: The model is cached in memory and ready to make predictions
    - *AVAILABLE*: The model is defined but not loaded, due to resource constraints
    - *FAILED*: The model is not loaded due to a different internal error
  
The complete specification can be found in the protocol buffer definition in the [protos](protos) directory.

## Troubleshooting

  * Newer versions of the model are not loaded.

    Check that the model has the extension .ftz or .bin and the path where the file has been uploaded.
    Also review your [config file](sample/config.yaml) to check that the model is listed in the *models* section

  * Predictions are too slow.

    Send all the predictions to the same model in bigger batches.
    Increase the maximum number of concurrent workers in the [service configuration](sample/config.yaml).

## Contact

You can open an issue in this project of just email your questions or comments to [Francisco Delgado](mailto:francisco.delgadodelhoyo@nielsen.com) or [Javier Tovar](mailto:javier.tovar@nielsen.com)

## Contribute

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

We recommend you to work in an isolated virtual environment:

```
git clone https://github.com/nielsen-oss/fasttext-serving
cd fasttext-serving
python3 -m venv venv
source venv/bin/activate
export SERVICE_CONFIG_PATH="sample/config.yaml"
python3 -m fts
```

And do not forget to pass the tests and add yours:

```
python3 test/test_suite.py
```

## License

This project is released under the terms of the [Apache 2.0 License](LICENSE).

## Acknowledgements

Big thanks to these third-party projects used by fastText Serving:

  - [fastText](https://fasttext.cc)
  - [grpc](https://github.com/grpc/grpc)
  - [watchdog](https://github.com/gorakhargosh/watchdog)
  - [PyYAML](https://github.com/yaml/pyyaml)
