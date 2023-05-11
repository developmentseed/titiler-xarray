# titiler-xarray

## Setup

```bash
# Install AWS CDK requirements
# Create Virtual env
$ python -m pip install --upgrade virtualenv
$ virtualenv .venv
$ python -m pip install -r requirements-dev.txt
$ npm install
```

## Running Locally

Note: The CDK  deployment (in `/stack`) depends on a Dockerfile which has some additional python dependencies and specifies versions. These are required when running the application on AWS Lambda. In order to simulate the AWS Lambda environment locally, you may want to install these dependencies in your virtual environment as well.

```bash
```bash
pip install -e .
uvicorn titiler.xarray.main:app --reload
```

## Testing

Tests use data generated locally by using `tests/fixtures/generate_test_*.py` scripts.

To run all the tests:

```bash
pytest
```

To run just one test:

```bash
pytest test_factory.py::test_get_info
```

## Deploy

```bash
# Create AWS env
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 npm run cdk -- bootstrap

# Deploy app
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 AWS_PROFILE=smce-veda-mfa npm run cdk -- deploy
```
