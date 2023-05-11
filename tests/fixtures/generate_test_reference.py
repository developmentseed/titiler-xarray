"""Create reference fixtures."""

from datetime import datetime, timedelta

import fsspec
import kerchunk.hdf
import netCDF4 as nc
import numpy as np
from kerchunk.combine import MultiZarrToZarr
from kerchunk.hdf import SingleHdf5ToZarr

def create_netcdf(filename, date):
    with nc.Dataset(filename, 'w', format='NETCDF4') as ds:
        time = ds.createDimension('time', None)
        lat = ds.createDimension('lat', 10)
        lon = ds.createDimension('lon', 10)

        times = ds.createVariable('time', 'f4', ('time',))        
        lats = ds.createVariable('lat', 'f4', ('lat',))
        lons = ds.createVariable('lon', 'f4', ('lon',))
        value = ds.createVariable('value', 'f4', ('time', 'lat', 'lon',))
        value.units = 'Unknown'

        lats[:] = np.arange(40.0, 50.0, 1.0)
        lons[:] = np.arange(-110.0, -100.0, 1.0)
        times[:] = [date]

        print('var size before adding data', value.shape)

        value[0, :, :] = np.random.uniform(0, 100, size=(10, 10))

        print('var size after adding first data', value.shape)
        xval = np.linspace(0.5, 5.0, 10)
        yval = np.linspace(0.5, 5.0, 10)
        value[1, :, :] = np.array(xval.reshape(-1, 1) + yval)

        print('var size after adding second data', value.shape)

# Set the start date for the observations
start_date = np.datetime64(datetime(2023, 5, 10))
end_date = np.datetime64(datetime(2023, 5, 11))

# Generate the two netCDF files
create_netcdf('tests/fixtures/observation_1.nc', start_date)
create_netcdf('tests/fixtures/observation_2.nc', end_date)

urls = ["tests/fixtures/observation_1.nc", "tests/fixtures/observation_2.nc"]
singles = []
for url in urls:
    with fsspec.open(url, mode="rb", anon=True) as infile:
        h5chunks = SingleHdf5ToZarr(infile, url, inline_threshold=100)
        singles.append(h5chunks.translate())

mzz = MultiZarrToZarr(
    singles, concat_dims=["time"]
)

out = mzz.translate("tests/fixtures/reference.json")
