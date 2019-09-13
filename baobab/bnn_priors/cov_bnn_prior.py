import numpy as np
import scipy.stats as stats
import lenstronomy.Util.param_util as param_util
from .base_bnn_prior import BaseBNNPrior

class CovBNNPrior(BaseBNNPrior):
    """BNN prior with marginally covariant parameters

    """
    def __init__(self, bnn_omega, components):
        """
        Note
        ----
        The dictionary attributes are copies of the config corresponding to each component.
        The number of attributes depends on the number of components.

        Attributes
        ----------
        components : list
            list of components, e.g. `lens_mass`
        lens_mass : dict
            profile type and parameters of the lens mass
        src_light : dict
            profile type and parameters of the source light
        """
        super(CovBNNPrior, self).__init__()
        if 'cov_info' not in bnn_omega:
            raise ValueError("cov_info must be specified in the config inside bnn_omega for CovBNNPrior")

        self.components = components 
        for comp in bnn_omega:
            if comp in self.components:
                # e.g. self.lens_mass = cfg.bnn_omega.lens_mass
                setattr(self, comp, bnn_omega[comp])

        self._check_cov_info_validity(cov_info)

    def _check_cov_info_validity(self):
        """Checks whether the information passed into cov_info is valid.

        """

        n_cov_params = self.cov_info['cov_params_list']
        cov_omega = self.cov_info['cov_omega']
        if len(cov_omega['mu']) != n_cov_params:
            raise ValueError("mu value in cov_omega should have same length as number of cov params in cov_params_list")
        if cov_omega['is_log'] is not None:
            if cov_omega['is_log'] != n_cov_params:
                raise ValueError("is_log value in cov_omega should have same length as number of cov params in cov_params_list")
        if not np.array_equal(cov_omega['cov_mat'], [n_cov_params, n_cov_params]):
            raise ValueError("cov_mat value in cov_omega should have shape [n_cov_params, n_cov_params]")

    def sample(self):
        """Gets kwargs of sampled parameters to be passed to lenstronomy

        Returns
        -------
        dict
            dictionary of config-specified components (e.g. lens mass), itself
            a dictionary of sampled parameters corresponding to the config-specified
            profile of that component

            """
        kwargs = {}
        for comp in self.components: # e.g. 'lens mass'
            kwargs[comp] = {}
            comp_omega = getattr(self, comp).copy() # e.g. self.lens_mass
            profile = comp_omega.pop('profile') # e.g. 'SPEMD'
            profile_params = comp_omega.keys()
            for param_name in profile_params: # e.g. 'theta_E'
                if (comp, param_name) not in self.cov_info['cov_params_list']:
                    hyperparams = comp_omega[param_name].copy()
                    kwargs[comp][param_name] = self.sample_param(hyperparams)

        # Fill in sampled values of covariant parameters
        cov_sample = self.sample_multivar_normal(self.cov_info['cov_omega'])
        for i, (comp, param_name) in enumerate(self.cov_info['cov_params_list']):
            kwargs[comp][param_name] = cov_sample[i]

        # Source pos is defined wrt the lens pos
        kwargs['src_light']['center_x'] += kwargs['lens_mass']['center_x']
        kwargs['src_light']['center_y'] += kwargs['lens_mass']['center_y']

        if 'lens_light' in self.components:
            # Lens light shares center with lens mass
            kwargs['lens_light']['center_x'] = kwargs['lens_mass']['center_x']
            kwargs['lens_light']['center_y'] = kwargs['lens_mass']['center_y']
        return kwargs

