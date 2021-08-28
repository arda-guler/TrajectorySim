DO NOT USE AS A GUIDANCE SYSTEM OR FLIGHT INSTRUMENT!

This program estimates the flight profile of a single stage 
sounding rocket launched directly upwards from the pad.

Important notes:
Lower time increments result in higher precision. <0.01 is suggested.

sounding_trajectory.py -- main simulation script

ApogeePredict.cpp      -- instant apogee prediction routine

atm_density_model.txt  -- Earth atmospheric density profile (US Standard Atmosphere 1976)
                       -- density in units of kg/m^3 with 100m steps (up to about 86km)
					   
atm_pressure_model.txt -- Earth atmospheric pressure profile (US Standard Atmosphere 1976)
                       -- pressure in units of Pa with 100m steps (up to about 86km)
					   
atm_temp_model.txt     -- Earth atmosphere temperature profile (US Standard Atmosphere 1976)
                       -- temperature in units of Kelvin with 100m steps (up to about 86km)
					   
atm_viscosity_model.txt-- Earth atmosphere viscosity profile (US Standard Atmosphere 1976)
                       -- viscosity in units of Pa.s with 100m steps (up to about 86km)  
