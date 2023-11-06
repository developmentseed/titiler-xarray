"""AWS Lambda handler."""

import logging
import sys

from mangum import Mangum

from titiler.xarray.main import app

logging.getLogger("mangum.lifespan").setLevel(logging.ERROR)
logging.getLogger("mangum.http").setLevel(logging.ERROR)

sys.path.append("/mnt/efs/libraries")
handler = Mangum(app, lifespan="off")
