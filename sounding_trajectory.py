#   SOUNDING ROCKET TRAJECTORY SIMULATOR
#   SINGLE STAGE ONLY (for now)

version = "1.0.2"

from dearpygui.core import *
from dearpygui.simple import *
import math
import pandas as pd
import time as t

#set initial window configuration (purely cosmetic)
set_main_window_size(1300, 700)
set_main_window_title("Sounding Rocket Trajectory Simulator | MRS")
set_theme("Dark")

calc_run_number = 0

#variables to save values of last run
#saving in another variable in case user makes changes to the input fields before clicking Export
last_eev = None
last_mdot = None
last_mass_init = None
last_mass_final = None
last_alt_init = None
last_time_increment = None
last_exit_pressure = None
last_exit_area = None
last_cross_sec = None
last_drag_coeff = None
last_drag_model = None

last_results = []

# graph display toggles
is_ground_displayed = False
is_karman_displayed = False

set_value(name="progress", value=0)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                 FILE IMPORT/EXPORT
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def importFile():

    try:
        import_filepath = get_value("filepath_field")
        
        if not import_filepath[-4:] == ".txt":
            if import_filepath[-5:] == ".xlsx":
                log_warning("Exported .xlsx files don't contain input info. Trying " + import_filepath[:-5] + ".txt instead...", logger="Logs")
                import_filepath = import_filepath[:-5] + ".txt"
            else:
                import_filepath = import_filepath + ".txt"
            
        log_info("Importing inputs from " + import_filepath, logger="Logs")
        import_file = open(import_filepath, "r")
    except:
        log_error("Import failed. Check filepath.", logger="Logs")
        return

    try:
        import_lines = import_file.readlines()
        if not import_lines[0][18:-1] == version:
            log_warning("Save file version does not match software version. Import might fail.", logger="Logs")

        set_value(name="eev_field", value=import_lines[4][28:-5])
        set_value(name="mdot_field", value=import_lines[5][11:-6])
        set_value(name="mass_init_field", value=import_lines[6][14:-4])
        set_value(name="mass_final_field", value=import_lines[7][12:-4])
        set_value(name="alt_init_field", value=import_lines[8][18:-3])
        set_value(name="exit_pressure_field", value=import_lines[9][22:-4])
        set_value(name="exit_area_field", value=import_lines[10][18:-5])
        set_value(name="time_increment_field", value=import_lines[11][16:-3])

        if import_lines[14] == "Drag model ENABLED.\n":
            set_value(name="drag_model_checkbox", value=True)
            set_value(name="cross_sec_field", value=import_lines[12][39:-5])
            set_value(name="drag_coeff_field", value=import_lines[13][41:-1])
        else:
            set_value(name="drag_model_checkbox", value=False)
            set_value(name="cross_sec_field", value="Drag model disabled.")
            set_value(name="drag_coeff_field", value="Drag model disabled.")
            
    except:
        log_error("Import failed. Check file formatting.", logger="Logs")
        return

    log_info("Import successful.", logger="Logs")
    simulateTraj()

def exportFile():

    global version
    
    if not calc_run_number > 0:
        log_error("Cannot export. Run the calculations first.", logger="Logs")
        return

    show_item("progress_bar")
    setProgressBarOverlay("Attempting export...")
    excelFilename = get_value("filepath_field")

    # sanitize filename
    if not excelFilename == "" or excelFilename == None:
        log_info("Attempting export (this might take a while)...", logger = "Logs")
        if len(excelFilename) > 5 and excelFilename[-5:] == ".xlsx":
            exportFile = excelFilename
        elif len(excelFilename) > 4 and excelFilename[-4:] == ".txt":
            exportFile = excelFilename[:-4] + ".xlsx"
        else:
            exportFile = excelFilename + ".xlsx"

        # Actual writing to Excel happens here
        try:
            
            # map of last_results:
            #
            # [0]: thrust_list
            # [1]: time_list
            # [2]: alt_list
            # [3]: vel_list
            # [4]: ground_level_list
            # [5]: karman_line_list
            # [6]: external_pressure_list
            # [7]: gravity_list
            # [8]: accel_list
            # [9]: isp_list
            # [10]: drag_list
            # [11]: dyn_press_list

            setProgressBarOverlay("Preparing data for export...")

            global last_drag_model
            
            export_thrust = {'Time (s)': last_results[1],'Thrust (N)': last_results[0]}
            export_alt = {'Time (s)': last_results[1],'Altitude (m)': last_results[2]}
            export_vel = {'Time (s)': last_results[1],'Velocity (m/s)': last_results[3]}
            export_external_pressure = {'Time (s)': last_results[1],'Ext. Pressure': last_results[6]}
            export_gravity = {'Time (s)': last_results[1],'Gravity (m/s^2)': last_results[7]}
            export_accel = {'Time (s)': last_results[1],'Acceleration (m/s^2)': last_results[8]}
            export_isp = {'Time (s)': last_results[1],'Specific Impulse (s)': last_results[9]}
            if last_drag_model:
                export_drag = {'Time (s)': last_results[1],'Drag (N)': last_results[10]}
                export_dyn_press = {'Time (s)': last_results[1],'Dynamic Pressure (Pa)': last_results[11]}

            df_alt = pd.DataFrame(export_alt)
            df_vel = pd.DataFrame(export_vel)
            df_accel = pd.DataFrame(export_accel)
            df_thrust = pd.DataFrame(export_thrust)
            df_external_pressure = pd.DataFrame(export_external_pressure)
            df_gravity = pd.DataFrame(export_gravity)
            df_isp = pd.DataFrame(export_isp)
            if last_drag_model:
                df_drag = pd.DataFrame(export_drag)
                df_dyn_press = pd.DataFrame(export_dyn_press)

            with pd.ExcelWriter(exportFile) as writer:
                set_value(name="progress", value=0.11)
                setProgressBarOverlay("Writing altitude...")
                df_alt.to_excel(writer, sheet_name = 'Altitude')
                set_value(name="progress", value=0.22)
                setProgressBarOverlay("Writing velocity...")
                df_vel.to_excel(writer, sheet_name = 'Velocity')
                set_value(name="progress", value=0.33)
                setProgressBarOverlay("Writing acceleration...")
                df_accel.to_excel(writer, sheet_name = 'Acceleration')
                set_value(name="progress", value=0.44)
                setProgressBarOverlay("Writing thrust...")
                df_thrust.to_excel(writer, sheet_name = 'Thrust')
                set_value(name="progress", value=0.55)
                setProgressBarOverlay("Writing ext. press...")
                df_external_pressure.to_excel(writer, sheet_name = 'Ext. Press.')
                set_value(name="progress", value=0.66)
                setProgressBarOverlay("Writing gravity...")
                df_gravity.to_excel(writer, sheet_name = 'Gravity')
                set_value(name="progress", value=0.77)
                setProgressBarOverlay("Writing Isp...")
                df_isp.to_excel(writer, sheet_name = 'Isp')
                set_value(name="progress", value=0.88)
                if last_drag_model:
                    setProgressBarOverlay("Writing drag...")
                    df_drag.to_excel(writer, sheet_name = 'Drag')
                    set_value(name="progress", value=0.90)
                    setProgressBarOverlay("Writing dyn. press...")
                    df_dyn_press.to_excel(writer, sheet_name = 'Dyn. Press.')

                setProgressBarOverlay("Finishing xlsx export...")
  
            log_info("Successfully saved data to " + exportFile, logger = "Logs")
            
        except:
            log_error("Excel export failed.", logger = "Logs")

        setProgressBarOverlay("Saving inputs to TXT...")
        # Save given inputs to TXT
        try:
            set_value(name="progress", value=0.96)
            inputSaveFile = exportFile[0:-5] + ".txt"
            result_file = open(inputSaveFile, "w")
            result_file.write("Save file version " + version + "\n\n")
            result_file.write("INPUTS\n\n")
            result_file.write("Effective exhaust velocity: ")
            result_file.write(str(last_eev)+" m/s\n")
            result_file.write("Mass flow: ")
            result_file.write(str(last_mdot)+" kg/s\n")
            result_file.write("Initial mass: ")
            result_file.write(str(last_mass_init)+" kg\n")
            result_file.write("Final mass: ")
            result_file.write(str(last_mass_final)+" kg\n")
            result_file.write("Initial altitude: ")
            result_file.write(str(last_alt_init)+" m\n")
            result_file.write("Nozzle exit pressure: ")
            result_file.write(str(last_exit_pressure)+" Pa\n")
            result_file.write("Nozzle exit area: ")
            result_file.write(str(last_exit_area)+" m^2\n")
            result_file.write("Time increment: ")
            result_file.write(str(last_time_increment)+" s\n")
            result_file.write("Vessel cross-section (facing airflow): ")
            if last_drag_model:
                result_file.write(str(last_cross_sec)+" m^2\n")
            else:
                result_file.write(str(last_cross_sec)+"\n")
            result_file.write("Drag coefficient (launch configuration): ")
            result_file.write(str(last_drag_coeff)+"\n")
            if last_drag_model:
                result_file.write("Drag model ENABLED.\n")
            else:
                result_file.write("Drag model DISABLED.\n")
            result_file.write("\nOUTPUTS\n\n")
            result_file.write("Maximum altitude: ")
            result_file.write(str(get_value("alt_max"))+" m\n")
            result_file.write("Time to apoapsis: ")
            result_file.write(str(get_value("tt_apoapsis"))+" s\n")
            result_file.write("Maximum velocity: ")
            result_file.write(str(get_value("vel_max"))+" m/s\n")
            result_file.write("Time to max. velocity: ")
            result_file.write(str(get_value("tt_max_vel"))+" s\n")
            result_file.write("Flight time: ")
            result_file.write(str(get_value("flight_time"))+" s\n")
            result_file.write("Min. specific impulse: ")
            result_file.write(str(get_value("isp_min"))+" s\n")
            result_file.write("Max. specific impulse: ")
            result_file.write(str(get_value("isp_max"))+" s\n")
            result_file.write("Max. dynamic pressure: ")
            if last_drag_model:
                result_file.write(str(get_value("max_Q"))+" Pa\n")
            else:
                result_file.write("Drag model disabled.\n")
            result_file.write("Simulation export file: " + exportFile + "\n")
            result_file.close()
            log_info("Inputs saved in " + inputSaveFile, logger = "Logs")
        except:
            log_error("TXT export failed.", logger = "Logs")  
        
    else:
        log_warning("No filename provided. Export aborted.", logger = "Logs")
    set_value(name="progress", value=1)
    hide_item("progress_bar")
    log_info("Done.", logger = "Logs")
    set_value(name="progress", value=0)
    setProgressBarOverlay("")

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                SIMULATION SETUP
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def simulateTraj():
    
    global calc_run_number
    calc_run_number += 1
    log_info(message = "Run [" + str(calc_run_number) + "]: Simulating trajectory...", logger = "Logs")

    # get input values from entry fields

    drag_enabled = get_value("drag_model_checkbox")
    
    try:
        eev = float(get_value("eev_field"))
        mdot = float(get_value("mdot_field"))
        mass_init = float(get_value("mass_init_field"))
        mass_final = float(get_value("mass_final_field"))
        alt_init = float(get_value("alt_init_field"))
        exit_pressure = float(get_value("exit_pressure_field"))
        exit_area = float(get_value("exit_area_field"))
        time_increment = float(get_value("time_increment_field"))

        if drag_enabled:
            cross_sec = float(get_value("cross_sec_field"))
            drag_coeff = float(get_value("drag_coeff_field"))
        else:
            cross_sec = -1.0
            drag_coeff = -1.0
            
    except:
        log_error("Input error. Make sure all design parameters are float values.", logger = "Logs")
        return

    if mass_final >= mass_init:
        log_error("Final mass can not be larger than initial mass!", logger = "Logs")
        return

    # save these values in global scope, in case we want to export
    global last_eev, last_mdot, last_mass_init, last_mass_final, last_alt_init, last_time_increment, last_exit_area, last_exit_pressure, last_drag_model
    last_eev = eev
    last_mdot = mdot
    last_mass_init = mass_init
    last_mass_final = mass_final
    last_alt_init = alt_init
    last_exit_area = exit_area
    last_exit_pressure = exit_pressure
    last_time_increment = time_increment

    global last_cross_sec, last_drag_coeff

    if drag_enabled:
        last_drag_model = True
        last_cross_sec = cross_sec
        last_drag_coeff = drag_coeff
    else:
        last_drag_model = False
        last_cross_sec = "Drag model disabled."
        last_drag_coeff = "Drag model disabled."

    log_info("Inputs:\n" +
             "Eff. Ex. Vel: " + str(eev) + " m/s\n"
             "Mass Flow: " + str(mdot) + " kg/s\n"
             "Initial Mass: " + str(mass_init) + " kg\n"
             "Final Mass: " + str(mass_final) + " kg\n"
             "Initial Alt.: " + str(alt_init) + " m\n"
             "Exit Press.: " + str(exit_pressure) + " Pa\n"
             "Exit Area: " + str(exit_area) + " m^2\n"
             "Time Increment: " + str(time_increment) + " s\n"
             "Cross Section: " + str(cross_sec) + " m^2", logger = "Logs")


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

    # VERY TERRIBLE approximation of drag force on the vessel
    def calc_drag(velocity, altitude):

        if get_value("drag_model_checkbox"):
            # drag_coeff = 0.1
            drag = (0.5 * alt2dens(altitude) * velocity**2 * drag_coeff * cross_sec) * -sign(velocity)
            dynamic_press = 0.5 * alt2dens(altitude) * velocity**2

            return drag, dynamic_press
        
        else:
            return 0.0, 0.0

    def calc_grav(altitude):
        gravity = 9.80665 * (6369000/(6369000+altitude))**2
        return gravity

    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    #                   RUN SIMULATION
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    #set initial values
    
    alt = alt_init
    thrust = mdot * eev + exit_area * (exit_pressure - alt2press(alt_init))
    mass = mass_init
    vel = 0
    accel = 0
    external_pressure = alt2press(alt_init)
    isp = (thrust)/(mdot * 9.80665)
    set_value(name="isp_min", value=isp)
    drag = 0
    dyn_press = 0
    density = alt2dens(alt_init)
    gravity = -calc_grav(alt_init)
    time = 0
    
    time_list = []
    alt_list = []
    vel_list = []
    accel_list = []
    ground_level_list = []
    karman_line_list = []
    thrust_list = []
    external_pressure_list = []
    gravity_list = []
    isp_list = []
    drag_list = []
    dyn_press_list = []
    density_list = []

    is_going_up = True
    is_accelerating_up = True
    is_launching = True

    show_item("progress_bar")
    progress_loop = 0

    # BEGIN TIMESTEPS
    
    while (True):

        cycle_start = t.perf_counter()

        # update visualizer ---

        vis_scale = float(get_value("vis_scale_field"))
        clear_drawing("vis_canvas")

        if not get_value("lock_on_rocket"):
            # sea
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,1,680,380), pmax=space2screen(340,1,680,380), color=[0,100,255,255])
            draw_text(drawing="vis_canvas", pos=[space2screen(-340,1,680,380)[0], space2screen(340,1,680,380)[1] - 14], text="Sea Level", size=14, color=[0,100,255,255])
            
            # ground
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,int(alt_init/vis_scale)+1,680,380), pmax=space2screen(340,int(alt_init/vis_scale)+1,680,380), color=[0,255,0,255])
            draw_text(drawing="vis_canvas", pos=[space2screen(-340,int(alt_init/vis_scale)+1,680,380)[0], space2screen(-340,int(alt_init/vis_scale),680,380)[1] - 14], text="Ground", size=14, color=[0,255,0,255])

            # rocket
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,int(alt/vis_scale)+1,680,380), pmax=space2screen(0,int(alt/vis_scale)+5,680,380), color=[200,0,0,255])

            # plume
            if is_accelerating_up:
                draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,int(alt/vis_scale)-2,680,380), pmax=space2screen(0,int(alt/vis_scale)+1,680,380), color=[200,150,10,255])

            # Karman line
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,int(100000/vis_scale),680,380), pmax=space2screen(340,int(100000/vis_scale),680,380), color=[255,100,255,128])
            draw_text(drawing="vis_canvas", pos=[space2screen(-340,int(100000/vis_scale),680,380)[0], space2screen(-340,int(100000/vis_scale),680,380)[1] - 14], text="Karman Line", size=14, color=[255,100,255,128])

        else:
            -int((alt/vis_scale))
            
            # sea
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340, 170-int(alt/vis_scale), 680, 380), pmax=space2screen(340, 170-int(alt/vis_scale), 680, 380), color=[0,100,255,255])
            draw_text(drawing="vis_canvas", pos=space2screen(-340, 170-int(alt/vis_scale)+14, 680, 380), text="Sea Level", size=14, color=[0,100,255,255])
            
            # ground
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340, 170-int((alt-alt_init)/vis_scale), 680, 380), pmax=space2screen(340, 170-int((alt-alt_init)/vis_scale), 680, 380), color=[0,255,0,255])
            draw_text(drawing="vis_canvas", pos=space2screen(-340, 170-int((alt-alt_init)/vis_scale)+14, 680, 380), text="Ground", size=14, color=[0,255,0,255])

            # rocket
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,170,680,380), pmax=space2screen(0,175,680,380), color=[200,0,0,255])

            # plume
            if is_accelerating_up:
                draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,165,680,380), pmax=space2screen(0,170,680,380), color=[200,150,10,255])

            # Karman line
            draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340, 170+int((100000-alt)/vis_scale), 680, 380), pmax=space2screen(340, 170+int((100000-alt)/vis_scale), 680, 380), color=[255,100,255,128])
            draw_text(drawing="vis_canvas", pos=space2screen(-340, 170+int((100000-alt)/vis_scale)+14, 680, 380), text="Karman Line", size=14, color=[255,100,255,128])
        # --- --- --- --- --- ---

        if progress_loop < 1.0:
            progress_loop = progress_loop + 0.01
        else:
            progress_loop = 0.0

        set_value(name="progress", value=progress_loop)
        setProgressBarOverlay("Simulation running...")

        if is_launching:

            # not enough thrust at lift-off!
            if thrust < (-gravity * mass_init):
                log_error("Not enough thrust - vehicle won't lift off.", logger = "Logs")
                delete_series(series="Altitude", plot="alt_plot")
                set_value(name="alt_max", value="Not enough thrust at launch. Simulation terminated.")
                set_value(name="vel_max", value="")
                set_value(name="flight_time", value="")
                return
            
            is_launching = False

        thrust_list.append(thrust)
        time_list.append(time)
        alt_list.append(alt)
        vel_list.append(vel)
        ground_level_list.append(alt_init)
        karman_line_list.append(100000)
        external_pressure_list.append(external_pressure)
        gravity_list.append(-gravity)
        accel_list.append(accel)
        isp_list.append(isp)
        drag_list.append(drag)
        dyn_press_list.append(dyn_press)
        density_list.append(density)

        density = alt2dens(alt)
        
        time = time + time_increment

        if mass > mass_final:
            thrust = mdot * eev + exit_area * (exit_pressure - external_pressure)
        else:
            thrust = 0

        gravity = -calc_grav(alt)
        
        external_pressure = alt2press(alt)

        # don't provide thrust if propellants are depleted!
        if mass > mass_final:      
            vel = vel + ((thrust/mass) * time_increment) + (gravity * time_increment) + (drag/mass * time_increment)
            mass = mass - mdot * time_increment
        else:
            vel = vel + gravity * time_increment + drag/mass * time_increment

        alt = alt + vel * time_increment
        alt_g = alt - alt_init
        accel = thrust/mass + gravity + drag/mass
        isp = (thrust)/(mdot * 9.80665)
        drag, dyn_press = calc_drag(vel, alt)

        if is_going_up and vel < 0:
            is_going_up = False
            alt_max = alt
            set_value(name="tt_apoapsis", value=time)
            set_value(name="alt_max", value=alt_max)
            set_value(name="max_Q", value=max(dyn_press_list))

        if is_accelerating_up and not mass > mass_final:
            is_accelerating_up = False
            vel_max = vel
            set_value(name="tt_max_vel", value=time)
            set_value(name="vel_max", value=vel_max)
            set_value(name="accel_max", value=accel)
            set_value(name="isp_max", value=isp)
            set_value(name="cutoff_time", value=time)

        # vehicle reached ground!
        if alt < alt_init:
            flight_time = time
            set_value(name="flight_time", value=flight_time)
            log_info("Simulation completed.", logger="Logs")
            if time_increment > 0.1:
                log_warning("Time increment too large. Last simulation may be inaccurate.", logger = "Logs")
                
            set_value(name="progress", value=0)
            hide_item("progress_bar")
            setProgressBarOverlay("")

            set_value(name="alt", value=alt_init)
            set_value(name="alt_g", value="IMPACT!")
            set_value(name="vel", value=vel)
            set_value(name="time", value=time)
            
            break

        # reduce computation speed to real-time if user prefers
        if get_value("sim_mode"):
            cycle_dt = t.perf_counter() - cycle_start
            if get_value("realtime_graph"):
                t.sleep((time_increment-cycle_dt)*(1/time))
            else:
                t.sleep(time_increment-cycle_dt)
        
        set_value(name="alt", value=alt)
        set_value(name="alt_g", value=alt_g)
        set_value(name="vel", value=vel)
        set_value(name="time", value=time)

        if get_value("realtime_graph"):
            add_line_series(name="Altitude", plot="alt_plot",x=time_list, y=alt_list)
            add_line_series(name="Velocity", plot="vel_plot",x=time_list, y=vel_list)
            add_line_series(name="Acceleration", plot="accel_plot",x=time_list, y=accel_list)
            add_line_series(name="Thrust", plot="thrust_plot",x=time_list, y=thrust_list)
            add_line_series(name="External Pressure", plot="ext_press_plot",x=time_list, y=external_pressure_list)
            add_line_series(name="Gravity", plot="grav_plot",x=time_list, y=gravity_list)
            add_line_series(name="Isp", plot="isp_plot", x=time_list, y=isp_list)
            add_line_series(name="Drag", plot="drag_plot", x=time_list, y=drag_list)
            add_line_series(name="Dynamic Pressure", plot="dyn_press_plot", x=time_list, y=dyn_press_list) 

    setProgressBarOverlay("Updating graphs...")
    add_line_series(name="Altitude", plot="alt_plot",x=time_list, y=alt_list)
    add_line_series(name="Velocity", plot="vel_plot",x=time_list, y=vel_list)
    add_line_series(name="Acceleration", plot="accel_plot",x=time_list, y=accel_list)
    add_line_series(name="Thrust", plot="thrust_plot",x=time_list, y=thrust_list)
    add_line_series(name="External Pressure", plot="ext_press_plot",x=time_list, y=external_pressure_list)
    add_line_series(name="Gravity", plot="grav_plot",x=time_list, y=gravity_list)
    add_line_series(name="Isp", plot="isp_plot", x=time_list, y=isp_list)
    add_line_series(name="Drag", plot="drag_plot", x=time_list, y=drag_list)
    add_line_series(name="Dynamic Pressure", plot="dyn_press_plot", x=time_list, y=dyn_press_list)
    #add_line_series(name="Density", plot="density_plot", x=time_list, y=density_list)

    global last_results
    last_results = [thrust_list, time_list, alt_list, vel_list, ground_level_list, karman_line_list, external_pressure_list, gravity_list, accel_list, isp_list, drag_list, dyn_press_list]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                    USER INTERFACE
# - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def space2screen(space_x, space_y, screen_width, screen_height):
    
    screen_x = space_x + screen_width/2
    screen_y = -space_y + screen_height

    return [screen_x, screen_y]

# hacky function to update progress bar overlay text
# because dearpygui.simple doesn't have such a solution
def setProgressBarOverlay(overlay_str):
    internal_dpg.configure_item("progress_bar", overlay=overlay_str)

# toggle graph guidelines to aid the naked eye
def toggleGround():
    global is_ground_displayed
    if calc_run_number > 0:
        if is_ground_displayed:
            delete_series(series="Ground", plot="alt_plot")
            is_ground_displayed = False
        else:
            add_line_series(name="Ground", plot="alt_plot",x=last_results[1], y=last_results[4], color=[0, 255, 0, 255])
            is_ground_displayed = True
    else:
        log_warning("Run a calculation first!", logger = "Logs")

def toggleKarman():
    global is_karman_displayed
    if calc_run_number > 0:
        if is_karman_displayed:
            delete_series(series="Karman Line", plot="alt_plot")
            is_karman_displayed = False
        else:
            add_line_series(name="Karman Line", plot="alt_plot", x=last_results[1], y=last_results[5], color=[255, 0, 0, 255])
            is_karman_displayed = True
    else:
        log_warning("Run a calculation first!", logger = "Logs")

#FILE OPERATIONS BAR
with window("File I/O", width=1260, height=60, no_close=True, no_move=True):
    set_window_pos("File I/O", 10, 10)
    add_input_text(name="filepath_field", label="Filepath", tip = "If the file is in the same directory with the script, you don't need\nto write the full path.")
    add_same_line()
    add_button("Import", callback = importFile)
    add_same_line()
    add_button("Export", callback = exportFile)
    add_same_line()
    add_progress_bar(name="progress_bar", source="progress", width=200, overlay="progress_overlay")
    hide_item("progress_bar")

#INPUTS WINDOW
with window("Input", width=550, height=360, no_close=True):   
    set_window_pos("Input", 10, 80)
    add_text("Enter parameters in float values.")
    add_spacing(count=6)
    add_input_text(name = "eev_field", label = "Effective Exhaust Vel. (m/s)")
    add_input_text(name = "mdot_field", label = "Mass Flow (kg/s)")
    add_input_text(name = "mass_init_field", label = "Initial Mass (kg)", tip="WET mass, not dry mass")
    add_input_text(name = "mass_final_field", label = "Final Mass (kg)", tip="Enter vehicle dry mass if all propellant will be used.")
    add_input_text(name = "alt_init_field", label = "Initial Altitude (m)")
    add_input_text(name = "exit_pressure_field", label = "Exhaust Exit Press. (Pa)")
    add_input_text(name = "exit_area_field", label = "Nozzle Exit Area (m^2)")
    add_input_text(name = "time_increment_field", label = "Time Increments (s)", tip="Enter lower values for higher precision.", default_value="0.01")
    add_spacing(count=6)
    add_checkbox(name = "drag_model_checkbox", label = "Enable the terrible drag model", tip="DON'T TRUST THIS!")
    add_input_text(name = "cross_sec_field", label = "Vessel Cross Section (m^2)", tip="Cross-sec facing the airflow.")
    add_input_text(name = "drag_coeff_field", label = "Drag Coefficient")
    add_spacing(count=6)
    add_text("Simulation Mode:")
    add_radio_button(name="sim_mode", items=["Quick Computation","Real-time Visualization"], default_value=0)
    add_spacing(count=6)
    add_button("Simulate Trajectory", callback = simulateTraj)
    add_same_line()
    add_checkbox(name = "realtime_graph", label = "Update graphs every cycle", tip="Looks really cool but significantly reduces performance.")

#OUTPUTS WINDOW
with window("Output", width=700, height=560, no_close=True):
    set_window_pos("Output", 570, 80)

    add_tab_bar(name="graph_switch")
    end("graph_switch")
    add_tab(name="graphs_tab", label="Graphs", parent="graph_switch")
    end("graphs_tab")
    add_tab(name="vis_tab", label="Visualization", parent="graph_switch")
    end("vis_tab")

    # VISUALIZER
    add_input_text(name="alt_max_output", label="Max. Altitude (m)", source="alt_max", readonly=True, enabled=False, parent="graphs_tab")
    add_input_text(name="max_vel_output", label="Max. Velocity (m/s)", source="vel_max", readonly=True, enabled=False, parent="graphs_tab")
    add_input_text(name="flight_time_output", label="Flight Time (s)", source="flight_time", readonly=True, enabled=False, parent="graphs_tab")

    add_input_text(name="alt_output", label="Altitude ASL (m)", source="alt", readonly=True, enabled=False, parent="vis_tab")
    add_input_text(name="alt_g_output", label="Altitude AGL (m)", source="alt_g", readonly=True, enabled=False, parent="vis_tab")
    add_input_text(name="vel_output", label="Velocity (m/s)", source="vel", readonly=True, enabled=False, parent="vis_tab")
    add_input_text(name="time_output", label="Mission Elapsed Time (s)", source="time", readonly=True, enabled=False, parent="vis_tab")

    add_slider_float(name="vis_scale_field", label="Scale (m/pixel)",
                     min_value=1.0, max_value=750.0, default_value=15.0,
                     clamped=True, parent="vis_tab", width=300)

    add_same_line(parent="vis_tab")
    add_checkbox(name="lock_on_rocket", label="Lock View on Rocket", parent="vis_tab")

    add_drawing("vis_canvas", parent="vis_tab", width=680, height=380)
    clear_drawing("vis_canvas")
    draw_rectangle(drawing="vis_canvas", pmin=space2screen(-340,1,680,380), pmax=space2screen(340,1,680,380), color=[0,100,255,255])
    draw_rectangle(drawing="vis_canvas", pmin=space2screen(0,1,680,380), pmax=space2screen(0,5,680,380), color=[200,0,0,255])

    # GRAPHS
    add_tab_bar(name="output_tabs", parent="graphs_tab")
    end("output_tabs")
    
    add_tab(name="alt_tab", label="Altitude", parent="output_tabs")
    end("alt_tab")
    add_tab(name="vel_tab", label="Velocity", parent="output_tabs")
    end("vel_tab")
    add_tab(name="accel_tab", label="Acceleration", parent="output_tabs")
    end("accel_tab")
    add_tab(name="thrust_tab", label="Thrust", parent="output_tabs")
    end("thrust_tab")
    add_tab(name="ext_press_tab", label="Ext. Press", parent="output_tabs")
    end("ext_press_tab")
    add_tab(name="grav_tab", label="Gravity", parent="output_tabs")
    end("grav_tab")
    add_tab(name="isp_tab", label="Isp", parent="output_tabs")
    end("isp_tab")
    add_tab(name="drag_tab", label="Drag", parent="output_tabs")
    end("drag_tab")
    add_tab(name="dyn_press_tab", label="Dyn. Press.", parent="output_tabs")
    end("dyn_press_tab")
    #add_tab(name="density_tab", label="Density", parent="output_tabs")
    #end("density_tab")
    
    add_input_text(name = "tt_apoapsis_output_field", label = "Time to Apoapsis (s)",
                   source="tt_apoapsis", readonly=True, enabled=False, parent ="alt_tab")
    add_plot(name="alt_plot", label="Altitude vs Time",
             x_axis_name="Time (s)", y_axis_name = "Altitude (m)", anti_aliased=True, parent="alt_tab")
    add_button(name="karman_line_toggle", label="Toggle Karman Line", parent="alt_tab", callback=toggleKarman)
    add_button(name="ground_toggle", label="Toggle Ground", parent="alt_tab", callback=toggleGround)

    add_input_text(name = "tt_max_vel_output_field", label = "Time to Max. Velocity (s)",
                   source="tt_max_vel", readonly=True, enabled=False, parent ="vel_tab")
    add_plot(name="vel_plot", label="Velocity vs Time",
             x_axis_name="Time (s)", y_axis_name = "Velocity (m/s)", anti_aliased=True, parent="vel_tab")

    add_input_text(name = "max_accel_output_field", label = "Max. Acceleration (m/s^2)",
                   source="accel_max", readonly=True, enabled=False, parent ="accel_tab")
    add_plot(name="accel_plot", label="Acceleration vs Time",
             x_axis_name="Time (s)", y_axis_name = "Acceleration (m/s^2)", anti_aliased=True, parent="accel_tab")

    add_input_text(name = "cutoff_time_output_field", label = "Engine Cutoff Time (s)",
                   source="cutoff_time", readonly=True, enabled=False, parent ="thrust_tab")
    add_plot(name="thrust_plot", label="Thrust vs Time",
             x_axis_name="Time (s)", y_axis_name = "Thrust (N)", anti_aliased=True, parent="thrust_tab")

    add_plot(name="ext_press_plot", label="External Pressure vs Time",
             x_axis_name="Time (s)", y_axis_name = "Pressure (Pa)", anti_aliased=True, parent="ext_press_tab")

    add_plot(name="grav_plot", label="Gravity vs Time",
             x_axis_name="Time (s)", y_axis_name = "Gravity (m/s^2)", anti_aliased=True, parent="grav_tab")

    add_input_text(name = "min_isp_output_field", label = "Min. Isp (s)",
                   source="isp_min", readonly=True, enabled=False, parent ="isp_tab")
    add_input_text(name = "max_isp_output_field", label = "Max. Isp (s)",
                   source="isp_max", readonly=True, enabled=False, parent ="isp_tab")
    add_plot(name="isp_plot", label="Specific Impulse (Isp) vs Time",
             x_axis_name="Time (s)", y_axis_name = "Specific Impulse (s)", anti_aliased=True, parent="isp_tab")

    add_plot(name="drag_plot", label="Drag vs Time",
             x_axis_name="Time (s)", y_axis_name = "Drag (N)", anti_aliased=True, parent="drag_tab")

    add_input_text(name = "max_Q_field", label = "Max. Q at Launch (Pa)",
                   source="max_Q", readonly=True, enabled=False, parent ="dyn_press_tab", tip="Max Q on the way up.")
    add_plot(name="dyn_press_plot", label="Dynamic Pressure vs Time",
             x_axis_name="Time (s)", y_axis_name = "Dynamic Pressure (Pa)", anti_aliased=True, parent="dyn_press_tab")

    #add_plot(name="density_plot", label="Density vs Time",
    #         x_axis_name="Time (s)", y_axis_name = "Density (kg/m^3)", anti_aliased=True, parent="density_tab")

#LOG WINDOW
with window("Log", width=550, height=190, no_close=True):
    set_window_pos("Log", 10, 450)
    add_logger("Logs", log_level=0, autosize_x = True, autosize_y = True)

start_dearpygui()
