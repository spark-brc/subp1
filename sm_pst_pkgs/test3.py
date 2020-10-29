# %%
import pandas as pd
import numpy as np
import time
from pyemu.pst.pst_utils import SFMT,IFMT,FFMT
import os
import csv


# %%
def extract_month_baseflow(sub_file, channels, start_day, cali_start_day, cali_end_day):
    """ extract a simulated baseflow rates from the output.sub file,
        store it in each channel file.

    Args:
        - sub_file (`str`): the path and name of the existing output file
        - channels (`list`): channel number in a list, e.g. [9, 60]
        - start_day ('str'): simulation start day after warm period, e.g. '1/1/1985'
        - end_day ('str'): simulation end day e.g. '12/31/2005'

    Example:
        sm_pst_utils.extract_month_baseflow('path', [9, 60], '1/1/1993', '1/1/1993', '12/31/2000')
    """
    gwqs = []
    subs = []
    for i in channels:
        sim_stf = pd.read_csv(
                        sub_file,
                        delim_whitespace=True,
                        skiprows=9,
                        usecols=[1, 3, 10, 11, 19],
                        names=["date", "filter", "surq", "gwq", "latq"],
                        index_col=0)
        
        sim_stf_f = sim_stf.loc[i]
        # sim_stf_f["filter"]= sim_stf_f["filter"].astype(str) 
        sim_stf_f = sim_stf_f[sim_stf_f['filter'].astype(str).map(len) < 13]
        sim_stf_f = sim_stf_f.drop(['filter'], axis=1)
        sim_stf_f.index = pd.date_range(start_day, periods=len(sim_stf_f.surq), freq='M')
        sim_stf_f = sim_stf_f[cali_start_day:cali_end_day]
        # sim_stf_f.to_csv('gwq_{:03d}.txt'.format(i), sep='\t', encoding='utf-8', index=True, header=False, float_format='%.7e')
        
        sim_stf_f['surq'] = sim_stf_f['surq'].astype(float)
        sim_stf_f['bf_rate'] = sim_stf_f['gwq']/ (sim_stf_f['surq'] + sim_stf_f['latq'] + sim_stf_f['gwq'])        
        bf_rate = sim_stf_f['bf_rate'].mean()
        # bf_rate = bf_rate.item()
        subs.append('bfr_{}'.format(i))
        gwqs.append(bf_rate)
        print('Average baseflow rate for {:03d} has been calculated ...'.format(i))
    # Combine lists into array
    bfr_f = np.c_[subs, gwqs]

    with open('baseflow_rate.out', "w", newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        for item in bfr_f:
            writer.writerow([(item[0]),
                '{:.4f}'.format(float(item[1])),
                "# name, monthly average baseflow rate"])

    print('Finished ...\n')

# %%

wd = "E:/okvg_pp/okvg_091120_pest"
extract_month_baseflow(
    os.path.join(wd, 'output.sub'), 
    [66, 68, 92, 147], '1/1/2003', '1/1/2003', '12/31/2007')
# %%
sim_stf = pd.read_csv(
                os.path.join(wd, 'output.sub'),
                delim_whitespace=True,
                skiprows=9,
                usecols=[1, 3, 10, 11, 19],
                names=["date", "filter", "surq", "gwq", "latq"],
                index_col=0)
sim_stf_f = sim_stf.loc[66]
sim_stf_f = sim_stf_f[sim_stf_f['filter'].astype(str).map(len) < 13]
sim_stf_f['surq'] = sim_stf_f['surq'].astype(float)

sim_stf_f['bf_rate'] = sim_stf_f['gwq']/ (sim_stf_f['surq'] + sim_stf_f['latq'] + sim_stf_f['gwq'])
sim_stf_f.loc[sim_stf_f['gwq'] < 0, 'bf_rate'] = 0

sim_stf_f

# %%
a = sim_stf_f['bf_rate'].mean()
type(a)
# %%
c = a.item()
# %%
type(c)
# %%
0/5

# %%
