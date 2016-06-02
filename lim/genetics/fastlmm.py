from __future__ import division

from numpy import exp
from numpy import atleast_2d
from numpy import clip

from limix_math.linalg import qs_decomposition

from .transformation import DesignMatrixTrans
from ..inference import FastLMM as FastLMMCore
from ..func import maximize_scalar
from ..func import Learnable
from ..func import Variables
from ..func import Scalar
from ..func import FuncData

class FastLMM(Learnable, FuncData):
    def __init__(self, y, X):
        self._logistic = Scalar(0.0)
        Learnable.__init__(self, Variables(logistic=self._logistic))
        FuncData.__init__(self)
        self._trans = DesignMatrixTrans(X)
        X = self._trans.transform(X)
        QS = qs_decomposition(X)
        self._flmmc = FastLMMCore(y, QS[0][0], QS[0][1], QS[1][0])
        self._genetic_variance = None
        self._noise_variance = None
        self._offset = None

        self._y = y
        self._QS = QS
        self._X = X

    def _delta(self):
        x = 1 / (1 + exp(-self._logistic.value))
        return clip(x, 1e-5, 1-1e-5)

    @property
    def genetic_variance(self):
        return self._genetic_variance

    @property
    def noise_variance(self):
        return self._noise_variance

    @property
    def offset(self):
        return self._offset

    def learn(self):
        maximize_scalar(self)

        delta = self._delta()
        self._flmmc.delta = delta

        offset = self._flmmc.offset
        scale = self._flmmc.scale

        self._genetic_variance = scale * (1 - delta)
        self._noise_variance = scale * delta
        self._offset = offset

    def value(self):
        self._flmmc.delta = self._delta()
        return self._flmmc.lml()

    def predict(self, Xp):
        Xp = atleast_2d(Xp)
        Xp = self._trans.transform(Xp)
        Cp = Xp.dot(self._X.T)
        Cpp = Xp.dot(Xp.T)
        return self._flmmc.predict(Cp, Cpp)
