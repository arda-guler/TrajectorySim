DO NOT USE AS A GUIDANCE SYSTEM OR FLIGHT INSTRUMENT!

This program estimates the flight profile of a single stage 
sounding rocket launched directly upwards from the pad.

Important notes:
Drag calculations are most likely inaccurate beyond subsonic region.
Lower time increments result in higher precision. <0.01 is suggested.

sounding_trajectory.py -- main simulation script

ApogeePredict.cpp      -- instant apogee prediction routine

atm_density_model.txt  -- Earth atmospheric density profile (US Standard Atmosphere 1976)
                       -- density in units of kg/m^3 with 100m steps (up to about 86km)
					  
