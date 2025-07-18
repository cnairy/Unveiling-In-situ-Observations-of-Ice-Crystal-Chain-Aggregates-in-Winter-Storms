#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Sep 11 13:31:13 2024

@author: Christian Nairy

Purpose: To match the CRS & CPL data with the P3 data (with chain aggregates)

Syntax: ./CPL_P3_match.py
"""
#Imports
import sys
sys.path.append('/home/chains/Documents/phd/github_repos/impacts_tools/src')
import pandas as pd
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
import proplot as pplt
from impacts_tools import p3, er2, radar_cmaps, match
from datetime import datetime
import matplotlib.dates as mdates
import warnings
import matplotlib.ticker as ticker
from matplotlib.ticker import LogFormatter
from matplotlib.ticker import LogLocator, LogFormatterMathtext, AutoMinorLocator
from matplotlib.colors import Normalize
from matplotlib import cm
from matplotlib.colors import LogNorm
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe


warnings.simplefilter("ignore") 

pplt.rc.update(
    suptitlesize=16, suptitleweight='bold', fontsize=14, ticklabelsize=14,
    ticklen=8, ticklenratio=0.5, colorbarwidth='1em',
    figurefacecolor='w', savefigtransparent=False
)
#%%
##############################################################################
##############################################################################
#Start
#Data and start/end times
date = '2022-01-19'
datestr = date.replace('-', '')
start, end = (np.datetime64('2022-01-19T12:31:00'), np.datetime64('2022-01-19T12:51:00'))

# CPL L1B data
fname_cpl_l1b = '/home/chains/Documents/phd/data/IMPACTS/ER2_Data/20220119/CPL_Data/IMPACTS_CPL_ATB_L1_20220119.hdf5'
cpl_l1b = er2.Cpl(fname_cpl_l1b, start_time=start, end_time=end)

# CPL L2 layer data (to get cloud top properties)
fname_cpl_l2lay = '/home/chains/Documents/phd/data/IMPACTS/ER2_Data/20220119/CPL_Data/IMPACTS_CPL_L2_V1-02_01kmLay_20220119.hdf5'
cpl_l2lay = er2.Cpl(fname_cpl_l2lay, l1b_trim_ref=cpl_l1b, start_time=start, end_time=end)

# CPL L2 profile data
fname_cpl_l2pro = '/home/chains/Documents/phd/data/IMPACTS/ER2_Data/20220119/CPL_Data/IMPACTS_CPL_L2_V1-02_01kmPro_20220119.hdf5'

cpl_l2pro = er2.Cpl(
    fname_cpl_l2pro, l1b_trim_ref=cpl_l1b, l2_cloudtop_ref=cpl_l2lay,
    l2_qc_ref=cpl_l2lay, start_time=start, end_time=end
)

fname_p3 = '/home/chains/Documents/phd/data/IMPACTS/aircraft_data/IMPACTS_MetNav_P3B_20220119_R0.ict' # P-3 IWG data
p3nav = p3.P3(
    fname_p3, date, start_time=start, end_time=end, tres='5S', fmt='ames'
)

# add cloud top properties (in L2 layers dataset) to the L1B dataset
cpl_l1b.data = cpl_l1b.get_cloudtop_properties(cpl_l2lay)

# get L1B data as same time resolution as L2 using nearest neighbor
cpl_l1b.data = cpl_l1b.data.interp(time=cpl_l2pro.data.time, method ='nearest')

#%%
#Import CRS Data
# read CRS data as xarray object
fname_crs = '/home/chains/Documents/phd/data/IMPACTS/ER2_Data/20220119/CRS_Data/IMPACTS2022_CRS_L1B_RevB_20220119.h5'
crs = er2.Crs(
    fname_crs, start_time=start, end_time=end,
    dataset=date[:4], dbz_sigma=1, vel_sigma=1
)


#%%
#The second snippet matches the L1B and L2 Profile datasets to the P-3 location and “builds” a P-3 
#track in ER-2 distance-relative framework, although you can easily 
#swap in “match_cpl.time_lidar” for the p3_x line of code to keep things time-relative instead:


# matched L1B data
match_cpl_l1b = match.Cpl(
    cpl_l1b.data, p3nav.data, query_k=30, dist_thresh=5000., time_thresh=600.,
    qc=True, ref_coords=None, n_workers=4
).data

# matched L2 data
match_cpl_l2pro = match.Cpl(
    cpl_l2pro.data, p3nav.data, query_k=15, dist_thresh=5000., time_thresh=600.,
    qc=False, ref_coords=None, n_workers=4
).data

match_cpl = xr.merge(
    [match_cpl_l1b, match_cpl_l2pro, p3nav.data.temp, p3nav.data.alt_gps],
    compat='override', combine_attrs='drop_conflicts'
)

match_cpl = match_cpl.where(match_cpl.pbsc_355) # drop pixels if no 355-nm data (optional)

# Match CRS data
match_crs = match.Crs(
    crs.data, p3nav.data, query_k=30, dist_thresh=5000,
    time_thresh=600, qc=True, ref_coords=None, n_workers=4
).data

#%%
match_crs = xr.merge(
    [match_crs, p3nav.data.temp, p3nav.data.alt_gps],
    compat='override', combine_attrs='drop_conflicts'
)


#%%
# build the P-3 track
valid_inds = (
    ~np.isnan(match_cpl.atb_532) & ~np.isnan(match_cpl.dpol_1064)
    & ~np.isnan(match_cpl.pbsc_532) & ~np.isnan(match_cpl.pbsc_355)
) # aggressive pixel filtering, not necessarily needed

p3_x = match_cpl.distance.where(valid_inds, drop=True).values / 1000. # km
p3_y = match_cpl.alt_gps.where(valid_inds, drop=True).values / 1000. # km
p3_time = pd.to_datetime(match_cpl.time.values[valid_inds])
p3_x1 = match_cpl.time_lidar.where(valid_inds, drop=True).values
p3_x2 = match_crs.time_radar.values
p3_y2 = match_cpl.alt_gps.values / 1000. # km



#%%
# print(p3_x1)
# print(match_crs.data.time_radar.values)
# match_cpl.data.to_netcdf(f'match.cpl_{datestr}.nc') # optionally save to file

#%%
#import chain aggregates and match to p3 time
#Import Hawkeye-CPI Particle Classification Dataset
path = '/home/chains/Documents/phd/data/IMPACTS/aircraft_data/'

try:
    data_cpi = np.loadtxt(path + '22_01_19_123000-125225.HawkeyeCPI.classify.merged.raw', skiprows=46)
except FileNotFoundError:
    print("The file does not exist.")
except Exception as e:
    print("An error occurred:", str(e))

data_cpi_pd = pd.DataFrame(data_cpi)

column_names = ['sfm','ImageNum','Plate','Skeleton_Plate','Sectored_Plate','SidePlane','Dendrite',
                'Column','Hollow_Column','Sheath','CappedColumn','Needle','Frozen_droplet','Bullet_rosette',
                'Graupel','Irregular','Droplet','Aggregate','Rimed','Pristine','Shattering','Multiple','Cutoff',
                'Elongated','ChainAgg','Sublimating','Empty','ConfidenceLevel','InterestingFlag']

data_cpi_pd.columns = column_names

#Replace nan values with 0's
data_cpi_pd.replace(99999.999, np.nan, inplace=True)

#%%
#number of chain aggs per second
data_cpi_pd.replace(0.0000, np.nan, inplace=True)

#make new columns for individual capped cols
data_cpi_pd['Individual_CapCol'] = 0

# Iterate through the rows and update 'Individual' column
for index, row in data_cpi_pd.iterrows():
    if pd.isna(row['ChainAgg']) or pd.isna(row['Aggregate']):
        for col in ['CappedColumn']:
            if row[col] == 1:
                data_cpi_pd.at[index, 'Individual_CapCol'] = 1

data_cpi_pd.replace(0.0000, np.nan, inplace=True)

# Filter out rows with values of 99999.999 and select the relevant columns
filtered_data = data_cpi_pd[data_cpi_pd['ChainAgg'] != 99999.999][['sfm', 'ChainAgg', 'Aggregate', 'Individual_CapCol']]

# Group the data by 'sfm' and compute the cumulative count for 'ChainAgg' and 'Aggregate'
grouped_data_chainagg = filtered_data.groupby('sfm')['ChainAgg'].count().cumsum()
chains = filtered_data.groupby('sfm')['ChainAgg'].count()
grouped_data_aggregate = filtered_data.groupby('sfm')['Aggregate'].count().cumsum()
grouped_data_individual_capcol = filtered_data.groupby('sfm')['Individual_CapCol'].sum().cumsum()

# Fill gaps
sfm_range_chainagg = np.arange(int(grouped_data_chainagg.index.min()), int(grouped_data_chainagg.index.max()) + 1)
sfm_range_aggregate = np.arange(int(grouped_data_aggregate.index.min()), int(grouped_data_aggregate.index.max()) + 1)
sfm_range_individual_capcol = np.arange(int(grouped_data_individual_capcol.index.min()), int(grouped_data_individual_capcol.index.max()) + 1)

grouped_data_filled_chainagg = grouped_data_chainagg.reindex(sfm_range_chainagg, method='ffill')
grouped_data_filled_aggregate = grouped_data_aggregate.reindex(sfm_range_aggregate, method='ffill')
grouped_data_filled_individual_capcol = grouped_data_individual_capcol.reindex(sfm_range_individual_capcol, method='ffill')

# Create a bar graph for 'ChainAgg' with gaps filled by the last value
x_chainagg = grouped_data_filled_chainagg.index
y_chainagg = grouped_data_filled_chainagg.values

# Create a bar graph for 'Aggregate' with gaps filled by the last value
x_aggregate = grouped_data_filled_aggregate.index
y_aggregate = grouped_data_filled_aggregate.values

# Create a bar graph for 'Individual_CapCol' with gaps filled by the last value
x_individual_capcol = grouped_data_filled_individual_capcol.index
y_individual_capcol = grouped_data_filled_individual_capcol.values


#DO COUNTS PER 5 SECONDS
chains.index = pd.to_datetime(chains.index, unit='s')

chains_1s = chains.resample('5S').sum()

# If you want to fill NaN values with a specific value (e.g., 0)
chains_1s = chains_1s.fillna(0)

# Create a bar graph for 'ChainAgg' with gaps filled by the last value

correct_date = pd.to_datetime('2022-01-19')
chains_1s.index = chains_1s.index.map(lambda x: x.replace(year=correct_date.year, month=correct_date.month, day=correct_date.day))


# x_chainagg_5s = chains_5s.index
# y_chainagg_5s = chains_5s.values



match_chains_1s = chains_1s[chains_1s.index.isin(p3_x2)]

#%%
#concentration (percentage) of chain aggregates per second

# Create a column 'time_seconds' assuming 'sfm' contains the time information in seconds
data_cpi_pd['time_seconds'] = data_cpi_pd['sfm'].astype(int)  # Convert to integer for second-based analysis

# Count total particles per second
particles_per_second = data_cpi_pd.groupby('time_seconds').size()

# Count ChainAgg particles per second
chainagg_per_second = data_cpi_pd[data_cpi_pd['ChainAgg'] == 1].groupby('time_seconds').size()

# Calculate percentage of ChainAgg per second
percentage_chainagg_per_second = (chainagg_per_second / particles_per_second) * 100

# Combine into a single DataFrame
chain_per = pd.DataFrame({
    'total_particles': particles_per_second,
    'chainagg_particles': chainagg_per_second,
    'percentage_chainagg': percentage_chainagg_per_second
}).fillna(0)

correct_date = pd.to_datetime('2022-01-19')
chain_per.index = pd.to_datetime(chain_per.index, unit='s') + pd.DateOffset(year=correct_date.year, month=correct_date.month, day=correct_date.day)

#Fill in gaps
start_time = chain_per.index.min()
end_time = chain_per.index.max()
full_time_range = pd.date_range(start=start_time, end=end_time, freq='S')  # 'S' is for seconds

# Reindex the DataFrame to ensure every second is present, filling gaps with 0
chain_per_full = chain_per.reindex(full_time_range).fillna(0)


matched_chain_per = chain_per_full[chain_per_full.index.isin(p3_x2)]

# First: reindex to include all times from p3_x2
matched_chain_per = chain_per_full.reindex(p3_x2).fillna(0)


#%%
#chains per 5 seconds

chain_per_5s = chain_per.resample('5S').sum()

# Recalculate percentage for each 5-second window
chain_per_5s['percentage_chainagg'] = (
    chain_per_5s['chainagg_particles'] / chain_per_5s['total_particles']
) * 100

# Step 1: Round p3_x2 to 5s and drop duplicates
p3_x2_5s = pd.to_datetime(p3_x2).round('5S')
p3_x2_5s = pd.DatetimeIndex(p3_x2_5s).drop_duplicates()

# Step 1: Round p3_x2 to nearest 5s
p3_x2_5s = pd.to_datetime(p3_x2).round('5S')

# Step 2: Create a DataFrame with time + alt
alt_df = pd.DataFrame({
    'time': p3_x2_5s,
    'alt_gps': p3_y2
})

# Step 3: Group by time and take the first (or mean, depending on your preference)
# This gives us one altitude value per 5-second bin
alt_df = alt_df.groupby('time').first().reset_index()

# Make sure chain_per_5s has 'time' as a column
chain_per_5s_filtered = chain_per_5s.reset_index()
chain_per_5s_filtered.columns = ['time'] + list(chain_per_5s_filtered.columns[1:])

# Inner merge to keep only times where alt exists
chain_per_5s_matched = pd.merge(chain_per_5s_filtered, alt_df, on='time', how='inner')

# Restore time as index (optional)
chain_per_5s_matched = chain_per_5s_matched.set_index('time')



#%%
#Section to add in other P3 microphysical data. HVPS, Temp
#Already have temp matched up: p3nav.data.temp

temp = p3nav.data.temp.values


#Read in HVPS data and create PSD and Norm. Particle Concentration for all bins
hvps_path = '/home/chains/Documents/phd/data/IMPACTS/aircraft_data/20220119/HVPS3B_Data/'
hvps_file = '22_01_19_10_51_34.HVPS3_Horizontal.conc.1Hz'

try:
    data_hvps = np.loadtxt(hvps_path + hvps_file, skiprows=52, usecols=(0,-7, -9))
except FileNotFoundError:
    print("The file does not exist.")
except Exception as e:
    print("An error occurred:", str(e))


# Create DataFrame with correct column names
data_hvps_pd = pd.DataFrame(data_hvps, columns=["Time", "Mean_Diameter", 'N_Conc'])

# Clean Data: Replace 0.0000 with NaN
data_hvps_pd.replace(0.0000, np.nan, inplace=True)

# Replace negative Mean_Diameter values with NaN (Just in case)
data_hvps_pd.loc[data_hvps_pd["Mean_Diameter"] < 0, "Mean_Diameter"] = np.nan

#convert N Conc. from #/m^3 to #/cm^3
data_hvps_pd['N_Conc_m3'] = data_hvps_pd['N_Conc']

# Convert 'Time' column to HH:MM:SS time using the reference date
data_hvps_pd['Time'] = pd.to_datetime(data_hvps_pd['Time'], unit='s') + pd.DateOffset(
    year=correct_date.year, month=correct_date.month, day=correct_date.day

)

#Match times
data_hvps_pd.set_index('Time', inplace=True)
hvps_matched = data_hvps_pd.reindex(full_time_range)
hvps_matched = data_hvps_pd.loc[data_hvps_pd.index.isin(p3_x2)]

# hvps_matched.loc[~hvps_matched.index.isin(p3_x2), "Mean_Diameter"] = np.nan



#%%
#Define Grid
def xsection_grid(x_grid, y_grid):
    '''
    Adds an extra element in the time/distance and height dimension to conform to newer mpl pcolormesh() function.
    Useful for plotting ER-2 radar cross sections.
    Parameters
    ----------
    x_grid: 2D time or distance field created from er2read() or resample() subroutines.
    y_grid: 2D height field created from er2read() or resample() subroutines.
    '''
    # Work with x coordinate (time/distance) first
    xdelta = x_grid[0, -1] - x_grid[0, -2] # should work on time and float dtypes
    vals_to_append = np.atleast_2d(np.tile(x_grid[0,-1] + xdelta, x_grid.shape[0])).T
    x_regrid = np.hstack((x_grid, vals_to_append)) # add column
    x_regrid = np.vstack((np.atleast_2d(x_regrid[0,:]), x_regrid)) # add row
    
    # Now do the y coordinate (height)
    ydelta = y_grid[0, :] - y_grid[1, :] # height difference between first and second gates
    vals_to_append = np.atleast_2d(y_grid[0,:] + ydelta)
    y_regrid = np.vstack((vals_to_append, y_grid)) # add row
    y_regrid = np.hstack((y_regrid, np.atleast_2d(y_regrid[:,-1]).T))
    return x_regrid, y_regrid

# construct meshgrids
#L1b
[X1, Y1] = xsection_grid(
    np.tile(np.atleast_2d(cpl_l1b.data.time), (cpl_l1b.data.height.shape[0], 1)),
    cpl_l1b.data.height / 1000.
)

#L2 Pro
[X1_l2, Y1_l2] = xsection_grid(
    np.tile(np.atleast_2d(cpl_l2pro.data.time), (cpl_l2pro.data.height.shape[0], 1)),
    cpl_l2pro.data.height / 1000.
)

#L2 Pro
[X1_l2, Y1_l2] = xsection_grid(
    np.tile(np.atleast_2d(cpl_l2pro.data.time), (cpl_l2pro.data.height.shape[0], 1)),
    cpl_l2pro.data.height / 1000.
)

#CRS
[X2, Y2] = xsection_grid(
    np.tile(np.atleast_2d(crs.data['time']), (len(crs.data['range']), 1)), # 2D time
    crs.data['height'] / 1000. # 2D height in km
)

#%%
crs_ldr_masked = np.where(
    (np.isnan(crs.data.dbz.values)) | (crs.data.dbz.values == 0),
    np.nan,  # or 0 if you prefer
    crs.data.ldr.values
)

crs_vel_masked = np.where(
    (np.isnan(crs.data.dbz.values)) | (crs.data.dbz.values == 0),
    np.nan,  # or 0 if you prefer
    crs.data.vel.values
)

cpl_atb_532_masked = np.where(
    (np.isnan(cpl_l2pro.data.dpol_1064.values)) | (cpl_l2pro.data.dpol_1064.values == 0),
    np.nan,  # or 0 if you prefer
    cpl_l1b.data.atb_532.values
)
#%%
# main plotting section
# Define a custom high-contrast colormap
colors = ["black", 'red', "blue", "magenta"]  # Bright, distinct colors
cmap_name = 'high_contrast'
n_bins = 100  # Number of bins in the color map
cm = LinearSegmentedColormap.from_list(cmap_name, colors, N=n_bins)

#Configure x-axis limits
start_time = mdates.date2num(datetime(2022, 1, 19, 12, 31))
end_time = mdates.date2num(datetime(2022, 1, 19, 12, 49))

# Overlay data for chain agg (5s average)
overlay_x = chain_per_5s_matched.index
overlay_y = chain_per_5s_matched['alt_gps']
size_vals = chain_per_5s_matched['percentage_chainagg']
size_scaled = np.clip(
    (chain_per_5s_matched['percentage_chainagg'] / 100) ** 0.8 * 600 + 40,
    40, 350
)
overlay_color = chain_per_5s_matched['percentage_chainagg']


#Plot 532 attenuated backscatter
fig, axs = pplt.subplots(nrows=3, ncols=2, refwidth=5, 
                         refaspect=2.5, sharey=False, sharex=False, dpi=300)

ax = axs[0,0]

dis = ax.plot(
    hvps_matched.index,
    hvps_matched["Mean_Diameter"],
    color="black", linewidth=1
)

# Set the Y-axis label with LaTeX-style formatting
ax.set_ylabel("")
ax.set_ylim(200, 1200)


# Add secondary y-axis for N_Conc_cm3
ax2 = ax.twinx()
ax2.plot(hvps_matched.index, hvps_matched["N_Conc_m3"], color='blue', linewidth=1)

# Log scale and ticks with 10^ formatting
ax2.set_yscale('log')
ax2.set_ylim(1e0, 1e6)
ax2.yaxis.set_major_locator(LogLocator(base=10.0, subs=[1.0], numticks=10))
ax2.yaxis.set_major_formatter(LogFormatterMathtext())
ax2.yaxis.set_minor_locator(LogLocator(base=10.0, subs=np.arange(2, 10) * 0.1, numticks=100))

# Tick appearance
ax2.tick_params(axis='y', which='major', length=8, width=2.0, color='blue', labelsize=14, labelcolor='blue')
ax2.tick_params(axis='y', which='minor', length=4, color='blue')
ax2.set_ylabel('')

# Set title using ax.text instead of urtitle
ax.text(0.98, 0.96, "HVPS-3B Mean Diameter [μm]", fontsize=16, fontweight='bold', ha='right', va='top', transform=ax.transAxes, color='black')
ax.text(0.98, 0.85, "HVPS-3B Total Concentration [# m$^{-3}$]", fontsize=16, fontweight='bold', ha='right', va='top', transform=ax.transAxes, color='blue')


ax.set_xlim(pd.to_datetime("2022-01-19 12:31:00"), pd.to_datetime("2022-01-19 12:51:00"))
ax.format(xformatter=mdates.DateFormatter('%H:%M'), xticklabels=[])
axs[0, 0].set_xlabel('')  # Top-left plot

ax.minorticks_on()  # Enable minor ticks
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))

ax.set_xlim(start_time, end_time)

# ------------

ax = axs[1,0]

c = ax.pcolormesh(
    X1, Y1, np.log10(cpl_atb_532_masked),
    levels=np.linspace(-4, 0, 41), rasterized=True,
    cmap='radar_NWSRefEnhanced', cmap_kw={'left': 0.2, 'right': 0.9},
    colorbar='r', colorbar_kw={'pad': '0em', 'ticks': 1}
)

ax.set_ylim(4, 8)
# Add 5 minor ticks on the x-axis
ax.minorticks_on()  # Enable minor ticks
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))  # Set 5 minor ticks

# print(chain_per_5s_matched['percentage_chainagg'].describe())

# Base flight track (thin black line)
ax.plot(p3_x2, p3_y2, color='black', linewidth=0.7, alpha=0.7, zorder=5)

sc_overlay = ax.scatter(
    overlay_x, overlay_y,
    c=size_vals,
    s=size_scaled,
    cmap=cm,               # your custom ["dimgrey", "black", "red", "magenta"]
    vmin=0,
    vmax=50,               # 🔥 this ensures 50% is mapped to the last color: magenta
    edgecolors='black',
    linewidths=0.3,
    zorder=10
)

# Add a colorbar for the scatter plot
# cbar_sc = fig.colorbar(sc, ax=ax, pad=0.1, orientation='vertical')
# cbar_sc.set_label('Chain Aggregates [% / 5 s]')
# cbar_sc.set_ticks([0, 1, 2, 3, 4, 5])  # Customize ticks as needed

ax.format(
    urtitle=r'CPL log$_{10}$($\beta_{532}$ [km$^{-1}$ sr$^{-1}$])',
    titleweight='bold'
)


ax.set_ylabel('Altitude [km]')
axs[1, 0].set_xlabel('')  # Middle-left plot

ax.set_xlim(start_time, end_time)


# -----------------

ax = axs[2,0]

d = ax.pcolormesh(
    X1_l2, Y1_l2, cpl_l2pro.data.dpol_1064.values,
    rasterized=True, levels=np.linspace(0, 0.8, 400),
    cmap='jet', cmap_kw={'left': 0, 'right': 1},
    colorbar='r', colorbar_kw={'pad': '0em', 'ticks': np.linspace(0, 0.8, 5)}
)

ax.set_ylim(4, 8)
# Add 5 minor ticks on the x-axis
ax.minorticks_on()  # Enable minor ticks
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))  # Set 5 minor ticks

# sc2 = ax.scatter(
#     p3_x2, p3_y2, c=matched_chain_per.percentage_chainagg, s=matched_chain_per.percentage_chainagg * 1.5 + 5
#     , label='Chain Aggregates [%]', zorder=10, cmap=cm,
# )

# Base flight track (thin black line)
ax.plot(p3_x2, p3_y2, color='black', linewidth=0.7, alpha=0.7, zorder=5)

sc_overlay = ax.scatter(
    overlay_x, overlay_y,
    c=size_vals,
    s=size_scaled,
    cmap=cm,               # your custom ["dimgrey", "black", "red", "magenta"]
    vmin=0,
    vmax=50,               # 🔥 this ensures 50% is mapped to the last color: magenta
    edgecolors='black',
    linewidths=0.3,
    zorder=10
)

# Add a colorbar for the scatter plot
# cbar_sc = fig.colorbar(sc2, ax=ax, pad=0.1, orientation='vertical')
# cbar_sc.set_label('Chain Aggregates [% / 5 s]')
# cbar_sc.set_ticks([0, 1, 2, 3, 4, 5])  # Customize ticks as needed

ax.format(
    urtitle='CPL Depolarization Ratio [δ]',
    titleweight='bold'
)

ax.set_ylabel('Altitude [km]')

# ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
# ax.set_xlabel('Time [UTC]\n(2022-01-19)')
ax.set_xlim(start_time, end_time)


# -----------------
# CRS Vert. Vel.

ax = axs[0,1]

cr = ax.pcolormesh(
    X2, Y2, crs.data.vel.values, cmap='BuRd', 
    rasterized=True, cmap_kw={'left': 0, 'right': 1}, colorbar='r',
    levels=np.linspace(-1.5, 1.5, 100), colorbar_kw={'pad': '0em', 'ticks': np.linspace(-1.5, 1.5, 3)}
)

ax.set_ylim(4, 8)
ax.set_ylabel('Altitude [km]')


from mpl_toolkits.axes_grid1.inset_locator import inset_axes

ax_top_right = axs[0, 1]  # Adjust if needed

# Create your temperature-colored scatter
t = ax_top_right.scatter(
    p3_x2, p3_y2, c=temp, s=4,
    cmap='thermal', vmin=-31.5, vmax=-29.5, zorder=10
)

# Create thicker inset axes above the top-right plot
cax_temp = inset_axes(
    ax_top_right,
    width="100%", height="35%",         # Thicker now!
    loc='lower center',
    bbox_to_anchor=(0.0, 1.0, 1.0, 0.25),  # Flush with top
    bbox_transform=ax_top_right.transAxes,
    borderpad=0
)

# Add horizontal colorbar
cbar_temp = fig.colorbar(t, cax=cax_temp, orientation='horizontal')

# Flip everything to appear **above** the colorbar
cbar_temp.ax.xaxis.set_label_position('top')
cbar_temp.ax.xaxis.set_ticks_position('top')

# Label and ticks
cbar_temp.set_label('Temperature [°C]', labelpad=5)
cbar_temp.set_ticks([-31.5, -30.5, -29.5])

cbar_temp.ax.tick_params(labelsize=14)

ax.minorticks_on()  # Enable minor ticks
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))

ax.format(
    urtitle=r"CRS Doppler Velocity [m s$^{-1}$]",
    titleweight='bold'
)

ax.set_xlim(start_time, end_time)


# -----------------
ax = axs[1,1]

cr = ax.pcolormesh(
    X2, Y2, crs.data.dbz.values, cmap='viridis', 
    rasterized=True, cmap_kw={'left': 0, 'right': 1}, colorbar='r',
    levels=np.linspace(-30, 15, 100), colorbar_kw={'pad': '0em', 'ticks': np.linspace(-30, 15, 6)}
)

ax.set_ylim(4, 8)

# sc2 = ax.scatter(
#     p3_x2, p3_y2, c=matched_chain_per.percentage_chainagg, s=matched_chain_per.percentage_chainagg * 1.5 + 5
#     , label='Chain Aggregates [%]', zorder=10, cmap=cm,
# )

# Base flight track (thin black line)
ax.plot(p3_x2, p3_y2, color='black', linewidth=0.7, alpha=0.7, zorder=5)

sc_overlay = ax.scatter(
    overlay_x, overlay_y,
    c=size_vals,
    s=size_scaled,
    cmap=cm,               # your custom ["dimgrey", "black", "red", "magenta"]
    vmin=0,
    vmax=50,               # 🔥 this ensures 50% is mapped to the last color: magenta
    edgecolors='black',
    linewidths=0.3,
    zorder=10
)

# Add a colorbar for the scatter plot
# cbar_sc = fig.colorbar(sc2, ax=ax, pad=0.1, orientation='vertical')
# cbar_sc.set_label('Chain Aggregates [% / 5 s]')
# cbar_sc.set_ticks([0, 1, 2, 3, 4, 5])  # Customize ticks as needed

ax.format(
    urtitle='CRS Reflectivity [dBZe]',
    titleweight='bold'
)
ax.set_ylabel('')


axs[1, 1].set_xlabel('')  # Middle-left plot
ax.minorticks_on()  # Enable minor ticks
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))

ax.set_xlim(start_time, end_time)


# -----------------

ax = axs[2,1]

cr = ax.pcolormesh(
    X2, Y2, crs_ldr_masked, cmap='jet', 
    rasterized=True, cmap_kw={'left': 0, 'right': 1}, colorbar='r',
    levels=np.linspace(-25, -17, 100), colorbar_kw={'pad': '0em', 'ticks': np.linspace(-25, -17, 5)}
)

ax.set_ylim(4, 8)

# sc2 = ax.scatter(
#     p3_x2, p3_y2, c=matched_chain_per.percentage_chainagg, s=matched_chain_per.percentage_chainagg * 1.5 + 5
#     , label='Chain Aggregates [%]', zorder=10, cmap=cm,
# )

# Base flight track (thin black line)
ax.plot(p3_x2, p3_y2, color='black', linewidth=0.7, alpha=0.7, zorder=5)

sc_overlay = ax.scatter(
    overlay_x, overlay_y,
    c=size_vals,
    s=size_scaled,
    cmap=cm,               # your custom ["dimgrey", "black", "red", "magenta"]
    vmin=0,
    vmax=50,               # this ensures 50% is mapped to the last color: magenta
    edgecolors='black',
    linewidths=0.3,
    zorder=10
)

# Add a colorbar for the scatter plot
# cbar_sc = fig.colorbar(sc2, ax=ax, pad=0.1, orientation='vertical')
# cbar_sc.set_label('Chain Aggregates [% / 5 s]')
# cbar_sc.set_ticks([0, 1, 2, 3, 4, 5])  # Customize ticks as needed
ax.set_ylabel('')

ax.format(
    urtitle='CRS Linear Depolarization Ratio [db]',
    titleweight='bold'
)


# ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
# ax.set_xlabel('Time [UTC]\n(2022-01-19)')

# Create a new shared colorbar axis beneath the entire 2x2 grid
# This colorbar will be used for the scatter Chain Aggregate % overlay
# Set the tick locations (every 10%)
ticks = [0, 10, 20, 30, 40, 50]
tick_labels = ['0%', '10%', '20%', '30%', '40%', '>50%']  # or r'\textbf{>50\%}' if using LaTeX


# Your colorbar
cbar_sc = fig.colorbar(
    sc_overlay,
    loc='bottom',
    label='Chain Aggregates [%]',
    length=0.3,
    width=0.15,
    ticks=ticks,
    ticklabelsize=14,
    space=4
)

# Apply to your colorbar
cbar_sc.set_ticks(ticks)
cbar_sc.ax.set_xticklabels(tick_labels)

#Axis managment
axs[0,0].format(xticklabels=[])
axs[0,1].format(xticklabels=[])
axs[1,0].format(xticklabels=[])
axs[1,1].format(xticklabels=[])




axs[2,0].format(
    xlabel='Time [UTC]\n(2022-01-19)',
    xformatter=mdates.DateFormatter('%H:%M')
)

axs[2,1].format(
    xlabel='Time [UTC]\n(2022-01-19)',
    xformatter=mdates.DateFormatter('%H:%M')
)

ax.minorticks_on()  # Enable minor ticks
ax.xaxis.set_minor_locator(ticker.AutoMinorLocator(5))


ax.set_xlim(start_time, end_time)

fig.subplots_adjust(top=0.9, bottom=0.12)  # Increase if x-labels are still squished

# #CRS VEL
# cr = ax.pcolormesh(
#     X2, Y2, crs.data.vel.values, cmap='viridis', 
#     rasterized=True, cmap_kw={'left': 0, 'right': 1}, colorbar='r',
#     levels=np.linspace(-2, 2, 100), colorbar_kw={'pad': '0em', 'ticks': 5}
# )

# ax.set_ylim(4, 8)

# sc2 = ax.scatter(
#     p3_x1, p3_y, c=match_chains_1s, s=3, label='Chain Aggregates [#]', zorder=10,
#     cmap='jet',
# )

# # Add a colorbar for the scatter plot
# cbar_sc = fig.colorbar(sc2, ax=ax, pad=0.1, orientation='vertical')
# cbar_sc.set_label('Chain Aggregates [#]')
# cbar_sc.set_ticks([0, 1, 2, 3, 4, 5])  # Customize ticks as needed

# ax.format(
#     urtitle='CRS Doppler Velocity [m/s]',
#     titleweight='bold'
# )












