# Releasing

This repository deploys to 2 stacks (one production and one development) via github actions. These deployments are intended to be services in beta for demonstration the NASA VEDA project.

The production stack will be deployed when main is tagged (aka "released"). The production stack has the domain https://prod-titiler-xarray.delta-backend.com.

The development stack will be deployed upon pushes to the dev and main branches. The development stack will have the domain https://dev-titiler-xarray.delta-backend.com.

Workflow:

1. PRs are made to `dev` branch. PRs should include tests and documentation. pytest should succeed before merging.
2. Once merged, https://dev-titiler-xarray.delta-backend.com will be deployed and should be manually tested.
3. When it is time to release changes to production, dev will be merged to main (no PR necessary).
4. The development deployment is updated to the latest commit on main. This should be manually tested again.
5. When ready, a release will be created on main by creating a tag. This will trigger the production deployment.
6. The production deployment (https://prod-titiler-xarray.delta-backend.com) should be manually tested.
