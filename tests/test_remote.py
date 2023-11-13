from test_app import get_variables_test

test_remote_netcdf_store = "https://nex-gddp-cmip6.s3-us-west-2.amazonaws.com/NEX-GDDP-CMIP6/GISS-E2-1-G/historical/r1i1p1f2/pr/pr_day_GISS-E2-1-G_historical_r1i1p1f2_gn_1950.nc"
test_remote_netcdf_store_params = {
    "params": {
        "url": test_remote_netcdf_store,
        "variable": "pr",
        "decode_times": False,
    },
    "variables": ["pr"],
}

def test_get_variables_remote_netcdf(app):
    return get_variables_test(app, test_remote_netcdf_store_params)
