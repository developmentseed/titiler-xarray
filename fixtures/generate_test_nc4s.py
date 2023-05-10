import kerchunk.hdf
from kerchunk.combine import MultiZarrToZarr
import fsspec
import numpy as np
import netCDF4 as nc
from datetime import datetime, timedelta

def create_netcdf(filename, date):
    with nc.Dataset(filename, 'w', format='NETCDF4') as dataset:
        # Create dimensions
        time_dim = dataset.createDimension('time', None)
        lat_dim = dataset.createDimension('lat', 180)
        lon_dim = dataset.createDimension('lon', 360)

        # Create variables
        times = dataset.createVariable('time', np.float64, ('time',))
        latitudes = dataset.createVariable('lat', np.float32, ('lat',))
        longitudes = dataset.createVariable('lon', np.float32, ('lon',))

        var1 = dataset.createVariable('var1', np.uint8, ('time', 'lat', 'lon'))
        var2 = dataset.createVariable('var2', np.uint8, ('time', 'lat', 'lon'))
        var3 = dataset.createVariable('var3', np.uint8, ('time', 'lat', 'lon'))
        var4 = dataset.createVariable('var4', np.uint8, ('time', 'lat', 'lon'))

        # Assign units and descriptions
        times.units = 'hours since 0001-01-01 00:00:00'
        times.calendar = 'gregorian'
        latitudes.units = 'degrees_north'
        longitudes.units = 'degrees_east'
        var1.units = 'unit1'
        var2.units = 'unit2'
        var3.units = 'unit3'
        var4.units = 'unit4'

        # Fill in data
        times[:] = nc.date2num([date], units=times.units, calendar=times.calendar)
        latitudes[:] = np.arange(-89.5, 90.5, 1.0)
        longitudes[:] = np.arange(-179.5, 180.5, 1.0)
        
        var1_data = np.random.randn(1, len(latitudes), len(longitudes))
        var2_data = np.random.randn(1, len(latitudes), len(longitudes))
        var3_data = np.random.randn(1, len(latitudes), len(longitudes))
        var4_data = np.random.randn(1, len(latitudes), len(longitudes))

        var1[:] = var1_data
        var2[:] = var2_data
        var3[:] = var3_data
        var4[:] = var4_data

# Set the start date for the observations
start_date = datetime(2023, 5, 10)

# Generate the two netCDF files
create_netcdf('fixtures/observation_1.nc', start_date)
create_netcdf('fixtures/observation_2.nc', start_date + timedelta(days=1))

urls = ['fixtures/observation_1.nc', 'fixtures/observation_2.nc']
so = dict(
    anon=True, default_fill_cache=False, default_cache_type='first'
)
singles = []
for u in urls:
    with fsspec.open(u, **so) as inf:
        h5chunks = kerchunk.hdf.SingleHdf5ToZarr(inf, u, inline_threshold=100)
        singles.append(h5chunks.translate())

mzz = MultiZarrToZarr(
    singles,
    remote_protocol="s3",
    remote_options={'anon': True},
    concat_dims=["time"]
)

out = mzz.translate('fixtures/reference.json')