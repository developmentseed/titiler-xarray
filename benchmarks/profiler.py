"""Profiler for titiler-xarray reader."""

import cProfile
import json
import logging
import pstats
import time
from io import StringIO
from typing import Callable, Dict, List, Optional

from loguru import logger as log


# This code is copied from marblecutter
#  https://github.com/mojodna/marblecutter/blob/master/marblecutter/stats.py
# License:
# Original work Copyright 2016 Stamen Design
# Modified work Copyright 2016-2017 Seth Fitzsimmons
# Modified work Copyright 2016 American Red Cross
# Modified work Copyright 2016-2017 Humanitarian OpenStreetMap Team
# Modified work Copyright 2017 Mapzen
class Timer(object):
    """Time a code block."""

    def __enter__(self):
        """Start timer."""
        self.start = time.time()
        return self

    def __exit__(self, ty, val, tb):
        """Stop timer."""
        self.end = time.time()
        self.elapsed = self.end - self.start


def parse_logs(logs: List[str]) -> Dict:
    """Parse S3FS Logs."""
    s3_get = len([line for line in logs if "get_object" in line])
    # s3_head = len([line for line in logs if "head_object" in line])
    # s3_list = len([line for line in logs if "list_object" in line])
    return {
        #         "LIST": s3_list,
        #         "HEAD": s3_head,
        "GET": s3_get,
    }


def profile(
    add_to_return: bool = False,
    quiet: bool = False,
    raw: bool = False,
    cprofile: bool = False,
    config: Optional[Dict] = None,
):
    """Profiling."""

    def wrapper(func: Callable):
        """Wrap a function."""

        def wrapped_f(*args, **kwargs):
            """Wrapped function."""
            # Catch s3fs Logs
            log_stream = StringIO()
            logger = logging.getLogger("s3fs")
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler(log_stream)
            logger.addHandler(handler)

            with Timer() as t:
                # cProfile is a simple Python profiling
                prof = cProfile.Profile()
                retval = prof.runcall(func, *args, **kwargs)
                profile_stream = StringIO()
                ps = pstats.Stats(prof, stream=profile_stream)
                ps.strip_dirs().sort_stats("time").print_stats()

            logger.removeHandler(handler)
            handler.close()

            s3fs_lines = log_stream.getvalue().splitlines()
            results = parse_logs(s3fs_lines)

            results["Timing"] = t.elapsed

            if cprofile:
                profile_lines = [p for p in profile_stream.getvalue().splitlines() if p]
                stats_to_print = [
                    p for p in profile_lines[3:13] if float(p.split()[1]) > 0.0
                ]
                results["cprofile"] = [profile_lines[2], *stats_to_print]

            if raw:
                results["s3fs"] = s3fs_lines

            if not quiet:
                log.info(json.dumps(results))

            if add_to_return:
                return retval, results

            return retval

        return wrapped_f

    return wrapper
