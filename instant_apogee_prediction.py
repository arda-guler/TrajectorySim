# APOGEE PREDICT LOOP

import math
import time as t

def simulateTraj():

    cycle_start = t.perf_counter()
    vel_init = 400
    alt_init = 3000
    mass = 130
    time_increment = 0.2
    cross_sec = 0.096
    drag_coeff = 0.4

    # Calculation sub-functions

    def clamp(num, min_value, max_value):
        return max(min(num, max_value), min_value)

    def sign(x): return 1 if x >= 0 else -1

    def alt2dens(altitude):

        if altitude > 85000:
            return 0.0
        else:
            # atmospheric density lookup file has values in kg/m^3, with steps of 100 meters
            # retrieved from https://www.digitaldutch.com/atmoscalc/table.htm
            model_filename = "atm_density_model.txt"
            model_file = open(model_filename, "r")
            model_lines = model_file.readlines()

            alt_low = int(altitude/100)
            alt_high = alt_low + 1

            lookup_line_low = float(model_lines[alt_low])
            lookup_line_high = float(model_lines[alt_high])

            # do linear interpolation so you don't get "staircase" values
            interpolated_density = lookup_line_low + ((lookup_line_high - lookup_line_low)/100) * ((altitude - (alt_low * 100)))

            return float(interpolated_density)

    # https://www.grc.nasa.gov/www/k-12/airplane/atmosmet.html
    def alt2press(altitude):

        # takes altitude in meters
        # returns typical pressure, density or temperature on demand
        # altitude: m
        # pressure: Pa
        # temp: degrees C

        if altitude < 11000:
            temp = -131.21 + 0.00299 * altitude
            press = 101330 * (1-((0.0065 * altitude)/(288.15)))**((9.807)/(286.9 * 0.0065))

        if 25000 > altitude >= 11000:
            temp = -56.46
            press = (22.65 * math.e ** (1.73 - 0.000157 * altitude)) * 1000

        if altitude >= 25000:
            temp = -131.21 + 0.00299 * altitude
            press = (2.488 * ((temp + 273.1)/(216.6))**(-11.388)) * 1000
        
        return press

    # Approximate drag force on the vessel
    def calc_drag(velocity, altitude):

        drag = (0.5 * alt2dens(altitude) * velocity**2 * drag_coeff * cross_sec) * -sign(velocity)      
        dynamic_press = 0.5 * alt2dens(altitude) * velocity**2

        return drag, dynamic_press

    def calc_grav(altitude):
        gravity = 9.80665 * (6369000/(6369000+altitude))**2
        return gravity

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                   RUN SIMULATION
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    #set initial values
    
    alt = alt_init
    vel = vel_init
    external_pressure = alt2press(alt_init)
    drag = 0
    dyn_press = 0
    density = alt2dens(alt_init)
    gravity = -calc_grav(alt_init)
    time = 0

    is_going_up = True

    # BEGIN TIMESTEPS
    
    while (True):

        density = alt2dens(alt)
        time = time + time_increment
        gravity = -calc_grav(alt)
        external_pressure = alt2press(alt)
        vel = vel + gravity * time_increment + drag/mass * time_increment
        alt = alt + vel * time_increment
        drag, dyn_press = calc_drag(vel, alt)

        if is_going_up and vel < 0:
            is_going_up = False
            alt_max = alt
            cycle_time = t.perf_counter() - cycle_start
            print("Apoapsis: " + str(alt_max))
            print("Computation time (s):" + str(cycle_time))
            print("Time Increments (s):" + str(time_increment))
            return

simulateTraj()
