## titiler-xarray

## Deploy

```bash
# Install AWS CDK requirements
$ pip install -r requirements-dev.txt
$ npm install

# Create AWS env
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 npm run cdk bootstrap

# Deploy app
$ AWS_DEFAULT_REGION=us-west-2 AWS_REGION=us-west-2 npm run cdk deploy
```
