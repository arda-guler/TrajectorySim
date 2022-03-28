# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# PROGRAM: EXPERIMENTAL LAUNCH VEHICLE GNC
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# DATE: 2022-03-28
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
# DESCRIPTION:
#
# REAL-TIME COMPUTATION OF STATE VECTORS BY KNOWN INITIAL
# STATE AND IMU INPUTS. APOAPSIS PREDICTION AND COMMANDING
# MAIN ENGINE SHUTDOWN.
# = = = = = = = = = = = = = = = = = = = = = = = = = = = = = =

import time

def init_atmo_model(model_filename):
    """Reads atmospheric density profile from file and saves
       it into memory."""

    # file extension check for user convenience
    if not model_filename.endswith(".txt"):
        model_filename += ".txt"
        
    model_file = open(model_filename, "r")
    model_lines = model_file.readlines()
    model_file.close()
    return model_lines

def init_state(a_init, v_init, m_init, mdot_init, m_final, a_target,
               A_cSec, c_drag_init, t_shutDelay, F_exp):
    """Initializes state vectors to pre-launch
       configuration."""

    # No additional computation required at this time.
    a = a_init
    v = v_init
    m = m_init
    mdot = mdot_init
    m_final = m_final
    a_target = a_target
    A_cSec = A_cSec
    c_drag = c_drag_init
    t_shutDelay = t_shutDelay
    F_exp = F_exp
    t = 0
    dt = 0.02
    state = "PRELAUNCH"

    return a, v, m, mdot, m_final, a_target, A_cSec, c_drag,\
           t_shutDelay, F_exp, t, dt, state

def update_state(a, v, m, mdot, m_final, accel, t, dt):
    """Updates state vectors using data provided by IMU."""

    if m > m_final:
        m -= mdot * dt
        
        if m < m_final:
            m = m_final
            
    v += accel * dt
    a += v * dt
    t += dt

    return a, v, m, mdot, t

def alt2dens(altitude, model_lines):
    """Returns atmospheric density at given altitude by
       reading atmospheric model data from memory."""
    
    if altitude > 85000:
        return 0.0
    else:
        alt_low = int(altitude/100)
        alt_high = alt_low + 1

        lookup_line_low = float(model_lines[alt_low])
        lookup_line_high = float(model_lines[alt_high])

        # do linear interpolation so you don't get "staircase" values
        interpolated_density = lookup_line_low + ((lookup_line_high - lookup_line_low)/100) * ((altitude - (alt_low * 100)))

        return float(interpolated_density)

def calc_grav(altitude):
    """Predicts gravitational acceleration at given altitude above Earth."""
    gravity = 9.80665 * (6369000/(6369000+altitude))**2
    return gravity

def calc_drag(velocity, altitude, drag_coeff, cross_sec, arr_atmDensity):
    """Predicts drag force experienced at given velocity and altitude."""
    drag = 0.5 * alt2dens(altitude, arr_atmDensity) * velocity**2 * drag_coeff * cross_sec
    return drag

def check_shutdown(a, v, m, mdot, m_final, a_target, A_cSec, c_drag,
                   t_shutDelay, F_exp, arr_atmDensity):
    """Predicts apoapsis and commands engine shutdown if the predicted
       apoapsis is at or above target altitude."""
    
    t = 0
    dt = 0.02
    accel = 0
    
    while v > 0:
        accel_gravity = calc_grav(a)
        F_drag = calc_drag(v, a, c_drag, A_cSec, arr_atmDensity)

        # if shutdown is yet to happen
        if t < t_shutDelay:

            # update mass
            if m > m_final:
                m -= mdot * dt

                if m < m_final:
                    m = m_final

            # update expected accel.
            accel = (F_exp - F_drag)/m
            accel -= accel_gravity

            # update state vectors
            v += accel * dt
            a += v * dt

            # update time
            t += dt

        # shutdown has happened
        elif t >= t_shutDelay:

            # mass update not required

            # update expected accel.
            accel = -F_drag/m
            accel -= accel_gravity

            # update state vectors
            v += accel * dt
            a += v * dt

            # update time
            t += dt

    # completed prediciton up to apoapsis
    # now, check if vessel reaches target altitude

    if a >= a_target:
        return True, a
    else:
        return False, a

def get_IMU_accel():
    # dummy function
    pass

def shutdown_engine():
    # dummy function
    pass

def main():
    """Main GNC function."""

    # initialize data
    arr_atmDensity = init_atmo_model("atm_density_model")
    a, v, m, mdot, m_final, a_target, A_cSec, c_drag,\
       t_shutDelay, F_exp, t, dt_init, state = init_state(900, 0, 10, 0.5, 2, 912.5, 0.096, 0.7, 0, 7900)

    dt = dt_init

    cmd_launch = False
    cmd_shutdown = False

    while state == "PRELAUNCH":
        # cmd_launch = check_launch_signal()
        if cmd_launch:
            state = "BOOST"
        else:
            pass

    while state == "BOOST":
        t_cycleStart = time.perf_counter()

        accel = get_IMU_accel()
        a, v, m, mdot, t = update_state(a, v, m, mdot, m_final, accel, t, dt)
        cmd_shutdown, a_predict = check_shutdown(a, v, m, mdot, m_final, a_target, A_cSec, c_drag, t_shutDelay, F_exp, arr_atmDensity)

        if cmd_shutdown:
            shutdown_engine()
            print("SHUTDOWN!")
            print("ALT, VEL, MASS, TIME, ALT_PREDICT")
            print(a, v, m, t, a_predict)

        # halt computation to match defined dt
        dt_actual = time.perf_counter() - t_cycleStart

        if dt > dt_actual:
            dt = dt_init
            time.sleep(dt - dt_actual)
        else:
            dt = dt_actual

main()
