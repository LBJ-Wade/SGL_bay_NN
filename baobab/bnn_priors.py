import numpy as np
import scipy.stats as stats
import lenstronomy.Util.param_util as param_util
from abc import ABC

class BNNPrior(ABC):
    def __init__(self):
        self.set_required_parameters()

    def set_required_parameters(self):
        """Defines a dictionary of the list of parameters (value) corresponding to each profile (key).

        The parameter names follow the lenstronomy convention.
        The dictionary will be updated as more profiles are supported.

        """
        params = dict(SPEMD=['center_x', 'center_y', 'gamma', 'theta_E', 'e1', 'e2'],
                          SHEAR_GAMMA_PSI=['gamma_ext', 'psi_ext'],
                          SERSIC_ELLIPSE=['amp', 'n_sersic', 'R_sersic', 'e1', 'e2'],
                          LENSED_POSITION=['amp'],
                          SOURCE_POSITION=['ra_source', 'dec_source', 'amp'],)
        setattr(self, 'params', params)

    def sample_param(self, hyperparams):
        """Assigns a sampling distribution

        """
        # TODO: see if direct attribute call is quicker than string comparison
        dist = hyperparams.pop('dist')
        if dist == 'beta':
            return self.sample_beta(**hyperparams)
        elif dist == 'normal':
            return self.sample_normal(**hyperparams)

    def sample_normal(self, mu, sigma, lower=-np.inf, upper=np.inf, log=False):
        """Samples from a normal distribution, optionally truncated

        Parameters
        ----------
        mu : float
            mean
        sigma : float
            standard deviation
        lower : float
            min value (default: -np.inf)
        upper : float
            max value (default: np.inf)
        log : bool
            is log-parameterized (default: False)
            if True, the mu and sigma are in dexes 

        Returns 
        -------
        float
            a sample from the specified normal

            """
        sample = stats.truncnorm((lower - mu)/sigma, (upper - mu)/sigma,
                                 loc=mu, scale=sigma).rvs()
        return sample

    def sample_multivar_normal(self, mu, cov_mat, lower=None, upper=None):
        """Samples from an N-dimensional normal distribution, optionally truncated

        An error will be raised if the cov_mat is not PSD.

        Parameters
        ----------
        mu : 1-D array_like, of length N
            mean
        cov_mat : 2-D array_like, of shape (N, N)
            symmetric, PSD matrix
        lower : None, float, or 1-D array_like, of length N
            min values (default: None)
        upper : None, float, or 1-D array_like, of length N
            max values (default: None)

        Returns
        -------
        float
            a sample from the specified N-dimensional normal

            """
        N = len(mu)
        if not (len(lower) == N and len(upper) == N):
            raise ValueError("lower and upper bounds must have length (# of parameters)")

        sample = np.random.multivariate_normal(mean=mu, cov=cov_mat, check_valid='raise')

        # TODO: get the PDF, scaled for truncation
        # TODO: issue warning if significant portion of marginal PDF is truncated
        if (lower is None) and (upper is None):
            return sample
        else:
            lower = -np.inf if lower is None else lower
            upper = np.inf if upper is None else upper
            # Reject samples outside of bounds, repeat sampling until accepted
            while not np.all([np.greater(sample, lower), np.greater(upper, sample)]):
                sample = np.random.multivariate_normal(mean=mu, cov=cov_mat)
            return sample

    def sample_beta(self, a, b, lower=0.0, upper=1.0):
        """Samples from a beta distribution, scaled/shifted

        Parameters
        ----------
        a : float
            first beta parameter
        b : float
            second beta parameter
        lower : float
            min value (default: 0.0)
        upper : float
            max value (default: 1.0)

        Returns 
        -------
        float
            a sample from the specified beta
        
        """
        sample = np.random.beta(a, b)
        sample = sample*(upper - lower) + lower
        return sample

class DiagonalBNNPrior(BNNPrior):
    """BNN prior with independent parameters

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
        super(DiagonalBNNPrior, self).__init__()
        self.components = components
        for comp in bnn_omega:
            if comp in self.components:
                # e.g. self.lens_mass = cfg.bnn_omega.lens_mass
                setattr(self, comp, bnn_omega[comp])

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
                hyperparams = comp_omega[param_name].copy()
                kwargs[comp][param_name] = self.sample_param(hyperparams)
        return kwargs


