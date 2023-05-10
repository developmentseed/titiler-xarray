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

```bash
uvicorn titiler.xarray.main:app --reload --port 8002
```

## Testing

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
