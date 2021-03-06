#######################################################################
#                                                                     #
#  Copyright 2014 Cristian C Lalescu                                  #
#                                                                     #
#  This file is part of pyNT.                                         #
#                                                                     #
#  pyNT is free software: you can redistribute it and/or modify       #
#  it under the terms of the GNU General Public License as published  #
#  by the Free Software Foundation, either version 3 of the License,  #
#  or (at your option) any later version.                             #
#                                                                     #
#  pyNT is distributed in the hope that it will be useful,            #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of     #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the      #
#  GNU General Public License for more details.                       #
#                                                                     #
#  You should have received a copy of the GNU General Public License  #
#  along with pyNT.  If not, see <http://www.gnu.org/licenses/>       #
#                                                                     #
#######################################################################

import numpy as np

t1ma_nm1 = {'0.90,009': 1.83,
            '0.90,019': 1.73,
            '0.90,029': 1.70,
            '0.90,039': 1.68,
            '0.90,059': 1.67,
            '0.90,099': 1.66,
            '0.90,199': 1.65,
            '0.99,009': 3.25,
            '0.99,019': 2.86,
            '0.99,029': 2.76,
            '0.99,039': 2.70,
            '0.99,059': 2.66,
            '0.99,099': 2.62,
            '0.99,199': 2.58}

def get_t1ma_nm1(
        onema,
        nm1):
    return t1ma_nm1['{0:.2f},{1:0>3}'.format(onema, nm1)]

class Wiener:
    def __init__(
            self,
            dt = 1.,
            nsteps = 128,
            noise_dimension = 1,
            solution_shape = [20, 16],
            p = 5):
        self.dt = dt
        self.nsteps = nsteps
        if len(solution_shape) == 2:
            self.nbatches = solution_shape[0]
            self.ntraj = solution_shape[1]
        self.noise_dimension = noise_dimension
        self.shape = [noise_dimension] + solution_shape
        self.solution_shape = solution_shape
        self.p = p
        self.r     = np.arange(1,self.p+1, 1).astype(np.float)
        for i in range(len(self.shape)):
            self.r = np.expand_dims(self.r, axis = len(self.r.shape))
        self.rho   = 1/12.        - .5*np.sum(1/self.r**2, axis = 0)/np.pi**2
        self.alpha = np.pi**2/180 - .5*np.sum(1/self.r**4, axis = 0)/np.pi**2
        self.Delta = dt
        self.sqrtD = np.sqrt(self.Delta)
        return None
    def initialize(
            self,
            rseed = None):
        np.random.seed(rseed)
        self.dW = np.sqrt(self.dt)*np.random.randn(
                *tuple([self.nsteps] + self.shape))
        self.W = np.zeros(
                tuple([self.nsteps + 1] + self.shape),
                dtype = self.dW.dtype)
        for t in range(self.nsteps):
            self.W[t+1] = self.W[t] + self.dW[t]
        return None
    def get_time(
            self):
        return self.dt*np.array(range(self.W.shape[0]))
    def coarsen(
            self,
            n = 2):
        new_object = Wiener(
                dt = n*self.dt,
                nsteps = int(self.nsteps/n),
                noise_dimension = self.noise_dimension,
                solution_shape = self.solution_shape,
                p = self.p)
        new_object.W = self.W[::n]
        return new_object
    def get_jj(self, Jj):
        # Gaussian
        zeta  = np.random.randn(*tuple([self.p] + list(Jj.shape)))
        eta   = np.random.randn(*tuple([self.p] + list(Jj.shape)))
        mu    = np.random.randn(*tuple(Jj.shape))
        phi   = np.random.randn(*tuple(Jj.shape))
        # additional quantities
        a = (- np.sqrt(2*self.Delta) * np.sum(eta / self.r, axis=0) / np.pi
             - (2*np.sqrt(self.Delta*self.rho)*mu))
        A = np.sum((zeta[:, :, np.newaxis]*eta[:, np.newaxis, :] - eta[:, :, np.newaxis]*zeta[:, np.newaxis, :])
                   / self.r[:, np.newaxis], axis = 0) / (2*np.pi)
        # multiple Stratonovich integrals
        Jj0  =  self.Delta*(Jj + a) / 2
        J0j  =  self.Delta*(Jj - a) / 2
        Jjj  =  (Jj[:, np.newaxis]*Jj[np.newaxis, :] / 2
              - (a [np.newaxis, :]*Jj[:, np.newaxis] - Jj[np.newaxis, :]*a[:, np.newaxis])/2
              +  self.Delta*A)
        # multiple Ito integrals
        Ijj = Jjj.copy()
        for j in range(Ijj.shape[0]):
            Ijj[j,j] -= .5*self.Delta
        return Jj0, J0j, Jjj, Ijj
    def get_jjj(self, Jj):
        # Gaussian
        zeta  = np.random.randn(*tuple([self.p] + list(Jj.shape)))
        eta   = np.random.randn(*tuple([self.p] + list(Jj.shape)))
        mu    = np.random.randn(*tuple(Jj.shape))
        phi   = np.random.randn(*tuple(Jj.shape))
        # additional quantities
        a = (- np.sqrt(2*self.Delta) * np.sum(eta / self.r,      axis=0) / np.pi
             - (2*np.sqrt(self.Delta*self.rho  )*mu))
        b = (  np.sqrt(self.Delta/2) * np.sum(eta / (self.r**2), axis=0)
             + (  np.sqrt(self.Delta*self.alpha)*phi))
        A = np.sum((zeta[:, :, np.newaxis]* eta[:, np.newaxis, :] - eta[:, :, np.newaxis]*zeta[:, np.newaxis, :])
                   / self.r     [:, np.newaxis], axis = 0) / (2*np.pi)
        B = np.sum((zeta[:, :, np.newaxis]*zeta[:, np.newaxis, :] + eta[:, :, np.newaxis]* eta[:, np.newaxis, :])
                   / (self.r**2)[:, np.newaxis], axis = 0) / (4*np.pi**2)
        C = np.zeros(B.shape, B.dtype)
        for i in range(self.p):
            for k in range(self.p):
                if not k == i:
                    C -= ((self.r[i] / (self.r[i]**2 - self.r[k]**2))
                        * (zeta[i, :, np.newaxis]*zeta[k, np.newaxis, :]/self.r[k]
                         - eta [i, :, np.newaxis]* eta[k, np.newaxis, :]*self.r[k]/self.r[i]))
        C /= 2*np.pi**2
        # multiple Stratonovich integrals
        Jj0  =  self.Delta*(Jj + a) / 2
        J0j  =  self.Delta*(Jj - a) / 2
        Jjj  =  (Jj[:, np.newaxis]*Jj[np.newaxis, :] / 2
              - (a [np.newaxis, :]*Jj[:, np.newaxis] - Jj[np.newaxis, :]*a[:, np.newaxis])/2
              +  self.Delta*A)
        J0j0 =  self.Delta**2*(Jj/6 -  b/np.pi)
        Jj00 =  self.Delta**2*(Jj/6 + b/(2*np.pi) + a/4)
        J00j =  self.Delta**2*(Jj/6 + b/(2*np.pi) - a/4)
        Jj0j = (self.Delta*Jj[:, np.newaxis]*Jj[np.newaxis, :]/6
              + a[:, np.newaxis]*J0j[np.newaxis, :]/2
              + self.Delta*(b[:, np.newaxis]*Jj[np.newaxis, :] + Jj[:, np.newaxis]*b[np.newaxis, :]) / (2*np.pi)
              - self.Delta**2 * B
              - self.Delta*Jj[:, np.newaxis]*a[np.newaxis, :] / 4)
        J0jj = (self.Delta*Jj[:, np.newaxis]*Jj[np.newaxis, :]/6
              - self.Delta*Jj[:, np.newaxis]*a[np.newaxis, :]/4
              + self.Delta*(-2*b[:, np.newaxis]*Jj[np.newaxis, :] + Jj[:, np.newaxis]*b[np.newaxis, :]) / (2*np.pi)
              + self.Delta**2 * (B + C + .5*A))
        Jjj0 = (self.Delta*Jj[:, np.newaxis]*Jj[np.newaxis, :]/2
              - self.Delta*(Jj[:, np.newaxis]*a[np.newaxis, :] - a[:, np.newaxis]*Jj[np.newaxis, :]) / 2
              + self.Delta**2 * A
              - Jj0j - J0jj)
        # multiple Ito integrals
        Ijj = Jjj.copy()
        for j in range(Ijj.shape[0]):
            Ijj[j,j] -= .5*self.Delta
        return Jj0, J0j, Jjj, Jjj0, Ijj

