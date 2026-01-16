# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 14:38:15 2025

@author: yberton
"""

from math import pi,log
import pandas as pd
from flowStudy.thermodynamics import Tsat 
pd.options.mode.copy_on_write = True

class CurrentPassageTube():
    
    def __init__(self):
        
        self.f_Twall_in_z = lambda Two,qeff_PH : Two + qeff_PH/(16*13.4)*(self.dext**2 - self.dint**2) - qeff_PH*self.dext**2/(8*13.4)*log(self.dext/self.dint)
         
    def get_data(self,df):
        self.df = df
        
    def pow_ratio(self, dt, pelec) :
        return(self.f_pow_ratio(dt,pelec))

    def Twiz(self,Two,qeff_PH) :
        """Calculate the inner wall temperature from the 
        outer wall temperature measurement and the effective heat at z"""
        return(self.f_Twall_in_z(Two,qeff_PH))
    
    def Tflz_1f(self,Tin,cp,q,z,mflow):
        """Calculate the fluid temperature at z in liquid state"""
        return Tin + (q*pi*self.dint*z)/(mflow*cp)
    
    def Tflz_2f(self, Tin, Pin, dP, z):
        """Calculate the fluid saturated temperature according to its pressure loss"""
        return(Tsat(Pin - dP*z/self.L),self.fluid)
        
    def velocity(self, mdot,rho) : 
        """Calculate the mean fluid velocity in the tube"""
        return mdot/rho/self.Sint
    
    def nloss_2ph(self):
        self.df_buff = self.df.copy()
        """Calculate the thermal loss coefficient for each line of the dataframe"""
        for i in range(len(self.df)):
            flag = 0
            j = 0
            if self.name == 'TS' : hmean = self.df.iloc[i]['h_TS_mean [W/m/K]'] ; pelec = self.df.iloc[i]['P_el_TS (W)']
            else : hmean = self.df.iloc[i]['h_PH_mean [W/m/K]'] ; pelec = self.df.iloc[i]['P_el_PH (W)']
            nloss = self.df.iloc[i]['nloss_exp [-]']
            nloss_1f = self.coeffs[0]*hmean**(-self.coeffs[1])
            while flag == 0:
                
                j+=1
                pth = pelec*(nloss - 1)
                qth = pth/self.Sin_clamps
                self.Twi_mean()
                self.Tf_1f_mean()
                self.h_mean()
                if self.name == 'TS' : hmean = self.df.iloc[i]['h_TS_mean [W/m/K]'] 
                else : hmean = self.df.iloc[i]['h_PH_mean [W/m/K]'] 
                nloss_new = self.coeffs[0]*hmean**(-self.coeffs[1])
                flag = (0.995 < nloss_new/nloss < 1.005)
                print(' nloss_new/nloss : ',  nloss_new/nloss)
                nloss = nloss_new
            
            self.df.iloc[i]
    
test = CurrentPassageTube()

