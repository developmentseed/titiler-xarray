## titiler-xarray

## Deploy

```bash
# Install AWS CDK requirements

# Create Virtual env and install python dependencies
python -m pip install --upgrade virtualenv
virtualenv .venv

source .venv/bin/activate
python -m pip install -r requirements-dev.txt

# Install node dependencies
npm install

# Create AWS env
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 npm run cdk -- bootstrap

# Deploy app
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 npm run cdk -- deploy
```
