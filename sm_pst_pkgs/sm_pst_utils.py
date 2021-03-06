""" PEST support utilities: 12/4/2019 created by Seonggyu Park
    last modified day: 09/14/2020 by Seonggyu Park
"""

import pandas as pd
import numpy as np
import time
from pyemu.pst.pst_utils import SFMT,IFMT,FFMT
import os
import shutil
import socket
import multiprocessing as mp
import csv


def extract_month_str(rch_file, channels, start_day, cali_start_day, cali_end_day):
    """extract a simulated streamflow from the output.rch file,
       store it in each channel file.

    Args:
        - rch_file (`str`): the path and name of the existing output file
        - channels (`list`): channel number in a list, e.g. [9, 60]
        - start_day ('str'): simulation start day after warm period, e.g. '1/1/1985'
        - end_day ('str'): simulation end day e.g. '12/31/2005'

    Example:
        sm_pst_utils.extract_month_str('path', [9, 60], '1/1/1993', '1/1/1993', '12/31/2000')
    """

    for i in channels:
        sim_stf = pd.read_csv(
                        rch_file,
                        delim_whitespace=True,
                        skiprows=9,
                        usecols=[1, 3, 6],
                        names=["date", "filter", "str_sim"],
                        index_col=0)

        sim_stf_f = sim_stf.loc[i]
        sim_stf_f = sim_stf_f[sim_stf_f['filter'] < 13]
        sim_stf_f = sim_stf_f.drop(['filter'], axis=1)
        sim_stf_f.index = pd.date_range(start_day, periods=len(sim_stf_f.str_sim), freq='M')
        sim_stf_f = sim_stf_f[cali_start_day:cali_end_day]
        sim_stf_f.to_csv('cha_{:03d}.txt'.format(i), sep='\t', encoding='utf-8', index=True, header=False, float_format='%.7e')
        print('cha_{:03d}.txt file has been created...'.format(i))
    print('Finished ...')


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
        sim_stf_f.loc[sim_stf_f['gwq'] < 0, 'bf_rate'] = 0     
        bf_rate = sim_stf_f['bf_rate'].mean()
        # bf_rate = bf_rate.item()
        subs.append('bfr_{:03d}'.format(i))
        gwqs.append(bf_rate)
        print('Average baseflow rate for {:03d} has been calculated ...'.format(i))
    # Combine lists into array
    bfr_f = np.c_[subs, gwqs]
    with open('baseflow_ratio.out', "w", newline='') as f:
        writer = csv.writer(f, delimiter='\t')
        for item in bfr_f:
            writer.writerow([(item[0]),
                '{:.4f}'.format(float(item[1]))
                ])
    print('Finished ...\n')


def extract_watertable_sim(grid_ids, start_day, end_day):
    """extract a simulated streamflow from the output.rch file,
        store it in each channel file.

    Args:
        - rch_file (`str`): the path and name of the existing output file
        - channels (`list`): channel number in a list, e.g. [9, 60]
        - start_day ('str'): simulation start day after warm period, e.g. '1/1/1985'
        - end_day ('str'): simulation end day e.g. '12/31/2000'

    Example:
        pest_utils.extract_month_str('path', [9, 60], '1/1/1993', '12/31/2000')
    """
    if not os.path.exists('swatmf_out_MF_obs'):
        raise Exception("'swatmf_out_MF_obs' file not found")
    if not os.path.exists('modflow.obs'):
        raise Exception("'modflow.obs' file not found")
    mf_obs_grid_ids = pd.read_csv(
                        'modflow.obs',
                        sep=r'\s+',
                        usecols=[3, 4],
                        skiprows=2,
                        header=None
                        )
    col_names = mf_obs_grid_ids.iloc[:, 0].tolist()

    # set index by modflow grid ids
    mf_obs_grid_ids = mf_obs_grid_ids.set_index([3])

    mf_sim = pd.read_csv(
                        'swatmf_out_MF_obs', skiprows=1, sep=r'\s+',
                        names=col_names,
                        usecols=grid_ids,
                        )
    mf_sim.index = pd.date_range(start_day, periods=len(mf_sim))
    mf_sim = mf_sim[start_day:end_day]
    for i in grid_ids:
        elev = mf_obs_grid_ids.loc[i].values  # use land surface elevation to get depth to water
        (mf_sim.loc[:, i] - elev).to_csv(
                        'wt_{}.txt'.format(i), sep='\t', encoding='utf-8',
                        index=True, header=False, float_format='%.7e'
                        )
        print('wt_{}.txt file has been created...'.format(i))


def str_obd_to_ins(srch_file, col_name, start_day, end_day):
    """extract a simulated streamflow from the output.rch file,
        store it in each channel file.

    Args:
        - rch_file (`str`): the path and name of the existing output file
        - channels (`list`): channel number in a list, e.g. [9, 60]
        - start_day ('str'): simulation start day after warm period, e.g. '1/1/1993'
        - end_day ('str'): simulation end day e.g. '12/31/2000'

    Example:
        pest_utils.extract_month_str('path', [9, 60], '1/1/1993', '12/31/2000')
    """ 

    stf_obd = pd.read_csv(
                        'streamflow.obd',
                        sep='\t',
                        usecols=['date', col_name],
                        index_col=0,
                        parse_dates=True,
                        na_values=[-999, '']
                        )
    stf_obd = stf_obd[start_day:end_day]

    stf_sim = pd.read_csv(
                        srch_file,
                        delim_whitespace=True,
                        names=["date", "str_sim"],
                        index_col=0,
                        parse_dates=True)

    result = pd.concat([stf_obd, stf_sim], axis=1)

    result['tdate'] = pd.to_datetime(result.index)
    result['month'] = result['tdate'].dt.month
    result['year'] = result['tdate'].dt.year
    result['ins'] = 'l1 w !{}_'.format(col_name) + result["year"].map(str) + result["month"].map('{:02d}'.format) + '!'
    result['{}_ins'.format(col_name)] = np.where(result[col_name].isnull(), 'l1', result['ins'])

    with open(srch_file+'.ins', "w", newline='') as f:
        f.write("pif ~" + "\n")
        result['{}_ins'.format(col_name)].to_csv(f, sep='\t', encoding='utf-8', index=False, header=False)
    print('{}.ins file has been created...'.format(srch_file))
    return result['{}_ins'.format(col_name)]


def mf_obd_to_ins(wt_file, col_name, start_day, end_day):
    """extract a simulated streamflow from the output.rch file,
        store it in each channel file.

    Args:
        - rch_file (`str`): the path and name of the existing output file
        - channels (`list`): channel number in a list, e.g. [9, 60]
        - start_day ('str'): simulation start day after warm period, e.g. '1/1/1993'
        - end_day ('str'): simulation end day e.g. '12/31/2000'

    Example:
        pest_utils.extract_month_str('path', [9, 60], '1/1/1993', '12/31/2000')
    """ 

    mf_obd = pd.read_csv(
                        'modflow.obd',
                        sep='\t',
                        usecols=['date', col_name],
                        index_col=0,
                        parse_dates=True,
                        )
    mf_obd = mf_obd[start_day:end_day]

    wt_sim = pd.read_csv(
                        wt_file,
                        delim_whitespace=True,
                        names=["date", "str_sim"],
                        index_col=0,
                        parse_dates=True)

    result = pd.concat([mf_obd, wt_sim], axis=1)

    result['tdate'] = pd.to_datetime(result.index)
    result['day'] = result['tdate'].dt.day
    result['month'] = result['tdate'].dt.month
    result['year'] = result['tdate'].dt.year
    result['ins'] = (
                    'l1 w !{}_'.format(col_name) + result["year"].map(str) +
                    result["month"].map('{:02d}'.format) +
                    result["day"].map('{:02d}'.format) + '!'
                    )
    result['{}_ins'.format(col_name)] = np.where(result[col_name].isnull(), 'l1', result['ins'])

    with open(wt_file+'.ins', "w", newline='') as f:
        f.write("pif ~" + "\n")
        result['{}_ins'.format(col_name)].to_csv(f, sep='\t', encoding='utf-8', index=False, header=False)
    print('{}.ins file has been created...'.format(wt_file))

    return result['{}_ins'.format(col_name)]


def extract_month_avg(cha_file, channels, start_day, cal_day=None, end_day=None):
    """extract a simulated streamflow from the channel_day.txt file,
        store it in each channel file.

    Args:
        - cha_file (`str`): the path and name of the existing output file
        - channels (`list`): channel number in a list, e.g. [9, 60]
        - start_day ('str'): simulation start day after warm period, e.g. '1/1/1993'
        - end_day ('str'): simulation end day e.g. '12/31/2000'

    Example:
        pest_utils.extract_month_str('path', [9, 60], '1/1/1993', '12/31/2000')
    """

    for i in channels:
        # Get only necessary simulated streamflow and convert monthly average streamflow
        os.chdir(cha_file)
        print(os.getcwd())
        df_str = pd.read_csv(
                            "channel_day.txt",
                            delim_whitespace=True,
                            skiprows=3,
                            usecols=[6, 8],
                            names=['name', 'flo_out'],
                            header=None
                            )
        df_str = df_str.loc[df_str['name'] == 'cha{:02d}'.format(i)]
        df_str.index = pd.date_range(start_day, periods=len(df_str.flo_out))
        mdf = df_str.resample('M').mean()
        mdf.index.name = 'date'
        if cal_day is None:
            cal_day = start_day
        else:
            cal_day = cal_day
        if end_day is None:
            mdf = mdf[cal_day:]
        else:
            mdf = mdf[cal_day:end_day]
        mdf.to_csv('cha_mon_avg_{:03d}.txt'.format(i), sep='\t', float_format='%.7e')
        print('cha_{:03d}.txt file has been created...'.format(i))
        return mdf


def model_in_to_template_file(model_in_file, tpl_file=None):
    """write a template file for a SWAT parameter value file (model.in).

    Args:
        model_in_file (`str`): the path and name of the existing model.in file
        tpl_file (`str`, optional):  template file to write. If None, use
            `model_in_file` +".tpl". Default is None
    Note:
        Uses names in the first column in the pval file as par names.

    Example:
        pest_utils.model_in_to_template_file('path')

    Returns:
        **pandas.DataFrame**: a dataFrame with template file information
    """

    if tpl_file is None:
        tpl_file = model_in_file + ".tpl"
    mod_df = pd.read_csv(
                        model_in_file,
                        delim_whitespace=True,
                        header=None, skiprows=0,
                        names=["parnme", "parval1"])
    mod_df.index = mod_df.parnme
    mod_df.loc[:, "tpl"] = mod_df.parnme.apply(lambda x: " ~   {0:15s}   ~".format(x[3:-4]))
    # mod_df.loc[:, "tpl"] = mod_df.parnme.apply(lambda x: " ~   {0:15s}   ~".format(x[3:7]))
    with open(tpl_file, 'w') as f:
        f.write("ptf ~\n")
        # f.write("{0:10d} #NP\n".format(mod_df.shape[0]))
        SFMT_LONG = lambda x: "{0:<50s} ".format(str(x))
        f.write(mod_df.loc[:, ["parnme", "tpl"]].to_string(
                                                        col_space=0,
                                                        formatters=[SFMT, SFMT],
                                                        index=False,
                                                        header=False,
                                                        justify="left"))
    return mod_df


def riv_par_to_template_file(riv_par_file, tpl_file=None):
    """write a template file for a SWAT parameter value file (model.in).

    Args:
        model_in_file (`str`): the path and name of the existing model.in file
        tpl_file (`str`, optional):  template file to write. If None, use
            `model_in_file` +".tpl". Default is None
    Note:
        Uses names in the first column in the pval file as par names.

    Example:
        pest_utils.model_in_to_template_file('path')

    Returns:
        **pandas.DataFrame**: a dataFrame with template file information
    """

    if tpl_file is None:
        tpl_file = riv_par_file + ".tpl"
    mf_par_df = pd.read_csv(
                        riv_par_file,
                        delim_whitespace=True,
                        header=None, skiprows=2,
                        names=["parnme", "chg_type", "parval1"])
    mf_par_df.index = mf_par_df.parnme
    mf_par_df.loc[:, "tpl"] = mf_par_df.parnme.apply(lambda x: " ~   {0:15s}   ~".format(x))
    with open(tpl_file, 'w') as f:
        f.write("ptf ~\n# modflow_par template file.\n")
        f.write("NAME   CHG_TYPE    VAL\n")
        f.write(mf_par_df.loc[:, ["parnme", "chg_type", "tpl"]].to_string(
                                                        col_space=0,
                                                        formatters=[SFMT, SFMT, SFMT],
                                                        index=False,
                                                        header=False,
                                                        justify="left"))
    return mf_par_df


def _remove_readonly(func, path, excinfo):
    """remove readonly dirs, apparently only a windows issue
    add to all rmtree calls: shutil.rmtree(**,onerror=remove_readonly), wk"""
    os.chmod(path, 128)  # stat.S_IWRITE==128==normal
    func(path)


# NOTE: Update description
def execute_beopest(
                master_dir, pst, num_workers=None, worker_root='..', port=4005, local=True,
                reuse_workers=None, restart=None):
    """Execute BeoPEST and workers on the local machine

    Args:
        master_dir (str): 
        pst (str): [description]
        num_workers ([type], optional): [description]. Defaults to None.
        worker_root (str, optional): [description]. Defaults to '..'.
        port (int, optional): [description]. Defaults to 4005.
        local (bool, optional): [description]. Defaults to True.
        reuse_workers ([type], optional): [description]. Defaults to None.

    Raises:
        Exception: [description]
        Exception: [description]
        Exception: [description]
        Exception: [description]
        Exception: [description]
        Exception: [description]
    """

    if not os.path.isdir(master_dir):
        raise Exception("master dir '{0}' not found".format(master_dir))
    if not os.path.isdir(worker_root):
        raise Exception("worker root dir not found")
    if num_workers is None:
        num_workers = mp.cpu_count()
    else:
        num_workers = int(num_workers)

    if local:
        hostname = "localhost"
    else:
        hostname = socket.gethostname()

    base_dir = os.getcwd()
    port = int(port)
    cwd = os.chdir(master_dir)
    os.system("start cmd /k beopest64 {0} /h :{1}".format(pst, port))
    time.sleep(1.5) # a few cycles to let the master get ready
    
    tcp_arg = "{0}:{1}".format(hostname,port)
    worker_dirs = []
    for i in range(num_workers):
        new_worker_dir = os.path.join(worker_root,"worker_{0}".format(i))
        if os.path.exists(new_worker_dir) and reuse_workers is None:
            try:
                shutil.rmtree(new_worker_dir, onerror=_remove_readonly)#, onerror=del_rw)
            except Exception as e:
                raise Exception("unable to remove existing worker dir:" + \
                                "{0}\n{1}".format(new_worker_dir,str(e)))
            try:
                shutil.copytree(master_dir,new_worker_dir)
            except Exception as e:
                raise Exception("unable to copy files from worker dir: " + \
                                "{0} to new worker dir: {1}\n{2}".format(master_dir,new_worker_dir,str(e)))
        elif os.path.exists(new_worker_dir) and reuse_workers is True:
            try:
                shutil.copyfile(pst, os.path.join(new_worker_dir, pst))
            except Exception as e:
                raise Exception("unable to copy *.pst from main worker: " + \
                                "{0} to new worker dir: {1}\n{2}".format(master_dir,new_worker_dir,str(e)))
        else:
            try:
                shutil.copytree(master_dir,new_worker_dir)
            except Exception as e:
                raise Exception("unable to copy files from worker dir: " + \
                                "{0} to new worker dir: {1}\n{2}".format(master_dir,new_worker_dir,str(e)))
        cwd = new_worker_dir
        os.chdir(cwd)
        os.system("start cmd /k beopest64 {0} /h {1}".format(pst, tcp_arg))


# TODO: copy pst / option to use an existing worker
def execute_workers(worker_rep, pst, host, num_workers=None, start_id=None, worker_root='..', port=4005, reuse_workers=None):
    """[summary]

    Args:
        worker_rep ([type]): [description]
        pst ([type]): [description]
        host ([type]): [description]
        num_workers ([type], optional): [description]. Defaults to None.
        start_id ([type], optional): [description]. Defaults to None.
        worker_root (str, optional): [description]. Defaults to '..'.
        port (int, optional): [description]. Defaults to 4005.

    Raises:
        Exception: [description]
        Exception: [description]
        Exception: [description]
        Exception: [description]
    """

    if not os.path.isdir(worker_rep):
        raise Exception("master dir '{0}' not found".format(worker_rep))
    if not os.path.isdir(worker_root):
        raise Exception("worker root dir not found")
    if num_workers is None:
        num_workers = mp.cpu_count()
    else:
        num_workers = int(num_workers)
    if start_id is None:
        start_id = 0
    else:
        start_id = start_id

    hostname = host
    base_dir = os.getcwd()
    port = int(port)
    cwd = os.chdir(worker_rep)
    tcp_arg = "{0}:{1}".format(hostname,port)

    for i in range(start_id, num_workers + start_id):
        new_worker_dir = os.path.join(worker_root,"worker_{0}".format(i))
        if os.path.exists(new_worker_dir) and reuse_workers is None:
            try:
                shutil.rmtree(new_worker_dir, onerror=_remove_readonly)#, onerror=del_rw)
            except Exception as e:
                raise Exception("unable to remove existing worker dir:" + \
                                "{0}\n{1}".format(new_worker_dir,str(e)))
            try:
                shutil.copytree(worker_rep,new_worker_dir)
            except Exception as e:
                raise Exception("unable to copy files from worker dir: " + \
                                "{0} to new worker dir: {1}\n{2}".format(worker_rep,new_worker_dir,str(e)))
        elif os.path.exists(new_worker_dir) and reuse_workers is True:
            try:
                shutil.copyfile(pst, os.path.join(new_worker_dir, pst))
            except Exception as e:
                raise Exception("unable to copy *.pst from main worker: " + \
                                "{0} to new worker dir: {1}\n{2}".format(worker_rep,new_worker_dir,str(e)))
        else:
            try:
                shutil.copytree(worker_rep,new_worker_dir)
            except Exception as e:
                raise Exception("unable to copy files from worker dir: " + \
                                "{0} to new worker dir: {1}\n{2}".format(worker_rep,new_worker_dir,str(e)))
                            
        cwd = new_worker_dir
        os.chdir(cwd)
        os.system("start cmd /k beopest64 {0} /h {1}".format(pst, tcp_arg))


