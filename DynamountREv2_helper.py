import numpy as np
import time
from TMC_2209.TMC_2209_StepperDriver import *

class Joint():
    def __init__(self, *, Theeta: int = 0, alfa: int = 0, r: int = 0, d: int = 0):
        self.Theeta = Theeta
        self.alfa = alfa
        self.r = r
        self.d = d

    @staticmethod
    def cosd(deg):
        return np.cos(np.deg2rad(deg))
    
    @staticmethod
    def sind(deg):
        return np.sin(np.deg2rad(deg))

    def matrix(self):
        return np.array([
            [self.cosd(self.Theeta), -self.sind(self.Theeta)*self.cosd(self.alfa),  self.sind(self.Theeta)*self.sind(self.alfa), self.r*self.cosd(self.Theeta)],
            [self.sind(self.Theeta),  self.cosd(self.Theeta)*self.cosd(self.alfa), -self.cosd(self.Theeta)*self.sind(self.alfa), self.r*self.sind(self.Theeta)],
            [0.0,                     self.sind(self.alfa),                         self.cosd(self.alfa),                        self.d],
            [0.0,                     0.0,                                          0.0,                                         1.0]
        ])
