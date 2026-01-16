"""
Surface finishes functions
"""
#imports
from math import exp,sin,cos,pi
from numpy import log
from scipy.special import lambertw

#Functions

"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                                      Friction factor
"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

f = lambda dint,dP,L,m_dot,rho : (pi*dP*dint**5*rho)/(32*L*m_dot**2) #Friction factor [-]
f_blasius = lambda Rel : 0.0791*Rel**(-0.25) #Blasius correlation for friction factor [-]

#Churchill correlation for friction factor [-]
A_churchill = lambda Rel, dinner, Rp : (2.457*log(( (7/Rel)**0.9 + (0.27*Rp)/(dinner) )**(-1)))**16
B_churchill = lambda Rel : (37530/Rel)**16
f_churchill = lambda coeff, Rel,dinner,Rp : coeff*((8/Rel)**12 + 1/((A_churchill(Rel,dinner,Rp) + B_churchill(Rel))**(3/2)) )**(1/12)

#W Lambert correlation
a_lambert = lambda Rel : 2.51/Rel
b_lambert = lambda dinner, Rp : Rp/(14.8*(dinner/2))
f_lambert = lambda Rel,dinner,Rp : 1/(2*lambertw(log(10)/2*a_lambert(Rel)*10**(b_lambert(dinner, Rp)/(2*a_lambert(Rel))))/log(10) - (b_lambert(dinner, Rp))/(a_lambert(Rel)))**2

