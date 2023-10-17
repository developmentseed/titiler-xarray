# Changelog

## v0.1.1

Support for NetCDF and making consolidated metadata optional. See https://github.com/developmentseed/titiler-xarray/pull/39.

[Performance results between prod (v0.1.0) and dev (unreleased)](https://github.com/developmentseed/tile-benchmarking/blob/bd1703209bbeab501f312d99fc51fda6bd419bf9/03-e2e/compare-prod-dev.ipynb).

* Performance for supported datasets is about the same.
* Unsupported datasets in v0.1.0 (netcdf and unconsolidated metadata) reported 100% errors in prod and 0% in dev (expected).
  * NetCDF Dataset: pr_day_ACCESS-CM2_historical_r1i1p1f1_gn_1950.nc
  * Unconsolidated metadata dataset: prod-giovanni-cache-GPM_3IMERGHH_06_precipitationCal


## v0.1.0 (2023-10-11)

Initial release of the project.
