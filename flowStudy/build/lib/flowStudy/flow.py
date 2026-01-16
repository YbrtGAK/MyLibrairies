"""
Flow functions
"""
#imports
from math import log,exp,sin,cos,pi

#Functions
G = lambda m_dot, Aint : m_dot/Aint
Re = lambda G,Dint,mu : G*Dint/mu 
