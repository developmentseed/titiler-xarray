# Releasing

This repository deploys to 2 stacks (one production and one development) via github actions. These deployments are intended to be services in beta for demonstration in [NASA's VEDA project](https://www.earthdata.nasa.gov/esds/veda).

The production stack will be deployed when main is tagged (aka "released"). The production stack has the domain https://prod-titiler-xarray.delta-backend.com.

The development stack will be deployed upon pushes to the dev and main branches. The development stack will have the domain https://dev-titiler-xarray.delta-backend.com.

## Release Workflow:

### Pre-release steps
1. PRs are made to `dev` branch. PRs should include tests and documentation. pytest should succeed before merging. If appropriate, changes should be added to the CHANGELOG.md file under "Next release".
2. Once merged, https://dev-titiler-xarray.delta-backend.com will be deployed and should be manually tested.

### Release steps

Before releasing, it is recommended to run benchmarks to compare performance between the development and production deployments. Run benchmarks between prod and dev via the [Run Benchmarks workflow in the tile-benchmarking repo](https://github.com/developmentseed/tile-benchmarking/actions/workflows/run-benchmarks.yml). Once the workflow completes, inspect the output of the "Upload results to S3" step for each environment to get the directory prefix for the past run. The output can be reviewed using the https://github.com/developmentseed/tile-benchmarking/blob/main/03-e2e/compare-prod-dev.ipynb notebook.


3. When it is time to release changes to production, add changes to CHANGELOG.md under a new release version and commit to dev. The `dev` branch will be merged to the `main` branch (no PR necessary).
4. The development deployment is updated to the latest commit on main. This should be manually tested again.
5. When ready, a release will be created on main by creating a tag. This will trigger the production deployment.
6. The production deployment (https://prod-titiler-xarray.delta-backend.com) should be manually tested.
