ARG PYTHON_VERSION=3.10

FROM --platform=linux/amd64 public.ecr.aws/lambda/python:${PYTHON_VERSION}

WORKDIR /tmp

COPY pyproject.toml pyproject.toml
COPY LICENSE LICENSE
COPY README.md README.md
COPY titiler/ titiler/

# Install dependencies
# HACK: aiobotocore has a tight botocore dependency
# https://github.com/aio-libs/aiobotocore/issues/862
# and becaise we NEED to remove both boto3 and botocore to save space for the package
# we have to force using old package version that seems `almost` compatible with Lambda env botocore
# https://docs.aws.amazon.com/lambda/latest/dg/lambda-runtimes.html
RUN pip install --upgrade pip
RUN pip install . "rio-tiler>=5.0.0" "cftime" "mangum>=0.10.0" "pandas==1.5.3" "botocore==1.29.76" "aiobotocore==2.5.0" "s3fs==2023.4.0" "fsspec==2023.4.0" "zarr==2.14.2" "xarray==0.19.0" -t /asset --no-binary pydantic

# Reduce package size and remove useless files
RUN cd /asset && find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[0-9]*//'); cp $f $n; done;
RUN cd /asset && find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
RUN cd /asset && find . -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN find /asset -type d -a -name 'tests' -print0 | xargs -0 rm -rf
RUN rm -rdf /asset/numpy/doc/ /asset/bin /asset/geos_license /asset/Misc
RUN rm -rdf /asset/boto3* /asset/botocore* /asset/scipy*

COPY infrastructure/aws/lambda/handler.py /asset/handler.py

CMD ["echo", "hello world"]
