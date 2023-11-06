"""AWS Lambda handler."""

import logging

from mangum import Mangum

import os
directory = '/mnt/efs/libraries'
contents = os.listdir(directory)
print(contents)
from titiler.xarray.main import app

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

handler = Mangum(app, lifespan="off")
