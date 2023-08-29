"""
External N-body / 2LPT solver that can be used to generate halos and density field.
The first one is 21cmFAST.
"""
import os
from .cosmo import *
from .functions import *
import time
import numpy as np


def initialise_21cmfast(param, data_dir=None):
    """
    Initialise the 21cmFAST parameters, and check the power spectrum of the initial conditions

    Parameters
    ----------
    param: Bunch
        The parameter file created using the beorn.par().
    data_dir: string
        The dir where to write the 21cmFAST cache data. Default is ./21cmFAST_data.
    Returns
    -------
    IC, pslin, klin : The initial conditions, followed by the power spectrum of the matter field.
    """

    import py21cmfast as p21c

    create_data_dir(data_dir)

    user_params = p21c.UserParams({"HII_DIM": param.sim.Ncell, "DIM": param.sim.Ncell * 3,
                                   "BOX_LEN": param.sim.Lbox / param.cosmo.h,
                                   "USE_INTERPOLATION_TABLES": True,
                                   # "FIXED_IC": True,
                                   "N_THREADS": param.sim.cores,
                                   })

    cosmo_params = p21c.CosmoParams(SIGMA_8=param.cosmo.s8,
                                    hlittle=param.cosmo.h,
                                    OMm=param.cosmo.Om,
                                    OMb=param.cosmo.Ob,
                                    POWER_INDEX=param.cosmo.ns,
                                    )
    Tvir = M_to_Tvir(param.source.M_min / param.cosmo.h, param.solver.z_end, param)
    astro_params = p21c.AstroParams({"ION_Tvir_MIN": Tvir})
    random_seed = param.sim.random_seed

    with p21c.global_params.use(INITIAL_REDSHIFT=300, CLUMPING_FACTOR=2.0):
        IC = p21c.initial_conditions(
            user_params=user_params,
            cosmo_params=cosmo_params,
            random_seed=random_seed,
            write=data_dir,
            direc=data_dir,
        )

    import tools21cm as t2c
    pslin, klin = t2c.power_spectrum_1d(IC.hires_density, kbins=20, box_dims=user_params.BOX_LEN)
    return IC, pslin, klin


def create_data_dir(data_dir):
    if data_dir is None:
        print('You have not specified a data_dir to store the 21cmFAST data. By default it is ./21cmFAST_data.')
        data_dir = './21cmFAST_data'
    if not os.path.isdir(data_dir):
        os.mkdir(data_dir)


def simulate_matter_21cmfast(param, IC=None, data_dir=None):
    import py21cmfast as p21c
    create_data_dir(data_dir)

    start_time = time.time()
    print('Simulating matter evolution with 21cmFast...')

    user_params = p21c.UserParams({"HII_DIM": param.sim.Ncell, "DIM": param.sim.Ncell * 3,
                                   "BOX_LEN": param.sim.Lbox / param.cosmo.h,
                                   "USE_INTERPOLATION_TABLES": True,
                                   # "FIXED_IC": True,
                                   "N_THREADS": param.sim.cores,
                                   })
    cosmo_params = p21c.CosmoParams(SIGMA_8=param.cosmo.s8,
                                    hlittle=param.cosmo.h,
                                    OMm=param.cosmo.Om,
                                    OMb=param.cosmo.Ob,
                                    POWER_INDEX=param.cosmo.ns,
                                    )
    Tvir = M_to_Tvir(param.source.M_min / param.cosmo.h, param.solver.z_end, param)
    astro_params = p21c.AstroParams({"ION_Tvir_MIN": 20.0})
    random_seed = 123456
    print('random seed is : ', random_seed)
    print('We will store halo catalogs in ', param.sim.halo_catalogs,'and density fields in ', param.sim.dens_field)

    redshift_list = def_redshifts(param)

    with p21c.global_params.use(INITIAL_REDSHIFT=300, CLUMPING_FACTOR=2.0):
        for redshift in redshift_list:
            if IC is None:
                IC, pslin, klin = initialise_21cmfast(param)

            perturbed_field = p21c.perturb_field(
                redshift=redshift,
                init_boxes=IC,
                # user_params=user_params,
                # cosmo_params=cosmo_params,
                # astro_params=astro_params,
                # random_seed=random_seed,
                write=data_dir,
                direc=data_dir,
            )
            halo_list = p21c.perturb_halo_list(
                redshift=redshift,
                init_boxes=IC,
                # user_params=user_params,
                # cosmo_params=cosmo_params,
                # astro_params=astro_params,
                # random_seed=random_seed,
                write=data_dir,
                direc=data_dir,
            )

            h0 = param.cosmo.h
            Lbox = param.sim.Lbox
            print('param.sim.Lbox is in Mpc/h. Halo catalogs catalogs have masses in Msol/h and positions in Mpc/h.')
            dens = perturbed_field.density
            halo_list = {'X': halo_list.halo_coords[:, 0] * Lbox / user_params.HII_DIM,
                         'Y': halo_list.halo_coords[:, 1] * Lbox / user_params.HII_DIM,
                         'Z': halo_list.halo_coords[:, 2] * Lbox / user_params.HII_DIM,
                         'M': halo_list.halo_masses * h0,
                         'z': redshift, 'Lbox': Lbox
                         }

            save_f(obj=dens, file=param.sim.dens_field + z_string_format(redshift) + '.0')
            save_f(obj=halo_list, file=param.sim.halo_catalogs + z_string_format(redshift))


    end_time = time.time()
    print('...done | Runtime =', print_time(end_time - start_time))
