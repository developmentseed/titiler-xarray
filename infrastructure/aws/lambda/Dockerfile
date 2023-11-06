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
RUN pip install . "mangum>=0.10.0" "botocore==1.29.76" "aiobotocore==2.5.0" -t /mnt/efs/libraries --no-binary pydantic

# Reduce package size and remove useless files
RUN cd /mnt/efs/libraries && find . -type f -name '*.pyc' | while read f; do n=$(echo $f | sed 's/__pycache__\///' | sed 's/.cpython-[0-9]*//'); cp $f $n; done;
RUN cd /mnt/efs/libraries && find . -type d -a -name '__pycache__' -print0 | xargs -0 rm -rf
RUN cd /mnt/efs/libraries && find . -type f -a -name '*.py' -print0 | xargs -0 rm -f
RUN find /mnt/efs/libraries -type d -a -name 'tests' -print0 | xargs -0 rm -rf
RUN rm -rdf /mnt/efs/libraries/numpy/doc/ /mnt/efs/libraries/bin /mnt/efs/libraries/geos_license /mnt/efs/libraries/Misc
RUN rm -rdf /mnt/efs/libraries/boto3*
RUN rm -rdf /mnt/efs/libraries/botocore*
ENV PYTHONPATH=/mnt/efs/libraries

COPY infrastructure/aws/lambda/handler.py /mnt/efs/libraries/handler.py

CMD ["echo", "hello world"]
