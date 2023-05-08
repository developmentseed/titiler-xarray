## titiler-xarray

## Deploy

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

```bash
# Currently the tiles tests require internect connectivity and a valid AWS account
export AWS_PROFILE=blah
pytest
```

## Deploy

```bash
# Create AWS env
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 npm run cdk -- bootstrap

# Deploy app
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 AWS_PROFILE=smce-veda-mfa npm run cdk -- deploy
```
