"""AWS Lambda handler."""

import logging

from mangum import Mangum

import sys
sys.path.append('/mnt/efs/libraries')
print(sys.path)
from titiler.xarray.main import app

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

handler = Mangum(app, lifespan="off")
