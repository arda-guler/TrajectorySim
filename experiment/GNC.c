/* 
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
PROGRAM: EXPERIMENTAL LAUNCH VEHICLE GNC 
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
DATE: 2022-03-28
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
DESCRIPTION:

REAL-TIME COMPUTATION OF STATE VECTORS BY KNOWN INITIAL
STATE AND IMU INPUTS. APOAPSIS PREDICTION AND COMMANDING
MAIN ENGINE SHUTDOWN.
= = = = = = = = = = = = = = = = = = = = = = = = = = = = = =
*/

#include <stdio.h>
#include <math.h>
#include <time.h>
#include <Windows.h>

// reads atmosphere density profile from file and holds it in memory
float* readAtmosphereModel() {
	FILE* fp;
	int n, i;
	float density_array[861];

	errno_t fop = fopen_s(&fp, "atm_density_model.txt", "r");
	if (fp == NULL) {
		printf("Failed to read atmospheric model file.\n\n");
		return 1;
	}

	n = 0;
	while (fscanf_s(fp, "%f", &density_array[n++]) != EOF)
		;

	fclose(fp);
	return density_array;
}

// dummy function
int checkLaunchSignal() {
	return 1;
}

// dummy function
float getAccelIMU() {
	return 40.0;
}

// returns atmospheric density at given altitude
float alt2dens(float alt, float* arr_atmDensity) {
	if (alt > 85000) {
		return 0.0f;
	}
	else {
		int alt_low = (int)(alt / 100);
		int alt_high = alt_low + 1;

		float lookup_line_low = arr_atmDensity[alt_low];
		float lookup_line_high = arr_atmDensity[alt_high];

		float interp_density = lookup_line_low + ((lookup_line_high - lookup_line_low) / 100) * ((alt - (alt_low * 100)));
		return interp_density;
	}
}

// predicts gravitational acceleration at given altitude
float calcGrav(float alt) {
	float grav = 9.80665 * pow((6369000 / (6369000 + alt)),2);
	return grav;
}

// predicts drag force at given velocity and altitude
float calcDrag(float vel, float alt, float c_drag, float A_cSec, float *arr_atmDensity) {
	float drag = 0.5f * alt2dens(alt, arr_atmDensity) * pow(vel, 2) * c_drag * A_cSec;
	return drag;
}

// updates state vectors using data provided by IMU
int updateState(float* alt, float* vel, float* mass, float* mass_flow_rate,
	float* mass_final, float* accel, float* time, float* dt) {

	if (*mass > *mass_final) {
		*mass = *mass - *mass_flow_rate * *dt;

		if (*mass < *mass_final) {
			*mass = *mass_final;
		}
	}

	*vel += *accel * *dt;
	*alt += *vel * *dt;
	*time += *dt;
}

// predicts apoapsis and commands engine shutdown if the predicted 
// apoapsis is at or above target altitude.
int checkShutdown(float alt, float vel, float mass, float mass_flow_rate, float mass_final,
	float a_target, float A_cSec, float c_drag, float t_shutDelay, float F_exp, float *arr_atmDensity) {

	float time = 0;
	float dt = 0.01;
	float accel = 0;
	
	while (vel > 0) {
		float accel_grav = calcGrav(alt);
		float F_drag = calcDrag(vel, alt, c_drag, A_cSec, arr_atmDensity);

		if (time < t_shutDelay) {

			//update mass
			if (mass > mass_final) {
				mass -= mass_flow_rate * dt;
				if (mass < mass_final) {
					mass = mass_final;
				}
			}

			accel = (F_exp - F_drag) / mass;
			accel -= accel_grav;

			// update state vectors
			vel += accel * dt;
			alt += vel * dt;

			// update time
			time += dt;
		}
		else {
			// mass update not required
			accel = -F_drag / mass;
			accel -= accel_grav;

			// update state vectors
			vel += accel * dt;
			alt += vel * dt;

			// update time
			time += dt;
		}
	}

	// apoapsis prediction complete, now check if vessel reaches target
	if (alt >= a_target) {
		return 1;
	}
	else {
		return 0;
	}
}

// main GNC function
int main() {
	float *arr_atmDensity = readAtmosphereModel();
	float alt = 900;
	float vel = 0;
	float mass = 200;
	float mass_flow_rate = 3;
	float mass_final = 120;
	float alt_target = 10000;
	float A_cSec = 0.096;
	float c_drag = 0.7;
	float t_shutDelay = 0;
	float F_exp = 7900;
	float time = 0;
	float dt_init = 0.005;

	float dt = dt_init;
	float dt_actual = 0;

	int cmd_launch = 0;
	int cmd_shutdown = 0;

	// PRELAUNCH state
	while (1) {
		cmd_launch = checkLaunchSignal();
		if (cmd_launch==1) {
			break;
		}
	}

	// BOOST state
	while (1) {
		clock_t cycle_begin = clock();

		float accel = getAccelIMU();

		// update state vectors
		if (mass > mass_final) {
			mass -= mass_flow_rate * dt;

			if (mass < mass_final) {
				mass = mass_final;
			}
		}

		vel += accel * dt;
		alt += vel * dt;
		time += dt;

		cmd_shutdown = checkShutdown(alt, vel, mass, mass_flow_rate, mass_final,
			alt_target, A_cSec, c_drag, t_shutDelay, F_exp, arr_atmDensity);

		//printf("%f  %f  %f\n", alt, vel, time);

		if (cmd_shutdown == 1) {
			printf("SHUTDOWN at altitude %f, velocity %f, time %f.", alt, vel, time);
		}

		if (alt < 900) {
			break;
		}

		clock_t cycle_end = clock();
		dt_actual = (cycle_end - cycle_begin)/CLOCKS_PER_SEC;
		if (dt > dt_actual) {
			dt = dt_init;
			Sleep(dt - dt_actual);
		}
		else {
			dt = dt_actual;
		}
	}

	return 0;
}