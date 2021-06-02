#include <stdio.h>
#include <math.h>
#include <time.h>

float vel, alt, mass;
float density_array[861];

int readAtmosphereModel() {
	FILE* fp;
	int n, i;

	errno_t fop = fopen_s(&fp, "atm_density_model.txt", "r");
	if (fp == NULL) {
		printf("Failed to read atmospheric density model file.\n\n");
		return 1;
	}

	n = 0;
	while (fscanf_s(fp, "%f", &density_array[n++]) != EOF)
		;

	fclose(fp);
	return 0;
}

//returns sign of a float value
int sign_f(float num) {
	if (num >= 0) {
		return 1;
	}
	else {
		return -1;
	}
}

//get density(kg/m^3) by altitude(m)
float alt2dens(float altitude) {
	//we don't have data for altitudes above 86km
	//(density at that point is practically zero anyway :P)
	if (altitude > 85000) {
		return 0.0f;
	}
	else {
		/*density values are provided in steps of 100 metres
		of altitude - we will do linear interpolation to
		get any values in between */
		int alt_low = (int)(altitude / 100);
		int alt_high = alt_low + 1;

		float lookup_val_low = density_array[alt_low];
		float lookup_val_high = density_array[alt_high];

		float interpolated_density = lookup_val_low + ((lookup_val_high - lookup_val_low) / 100) * ((altitude - (alt_low * 100)));

		return interpolated_density;
	}
}

float calcDrag(float altitude, float velocity) {

	float drag_coeff = 0.4;
	float cross_sec = 0.096;

	return (0.5f * alt2dens(altitude) * pow(velocity, 2) * drag_coeff * cross_sec) * -sign_f(velocity);
}

float calcGrav(float altitude) {
	float grav = 9.80665 * pow((6369000 / (6369000 + altitude)), 2);
	return 9.80665 * pow((6369000 / (6369000 + altitude)), 2);
}

//this is like a Riemann sum basically
float calcApogee(float alt_inst, float vel_inst, float mass_inst) {

	float alt = alt_inst;
	float vel = vel_inst;
	float mass = mass_inst;

	float drag = 0;
	float atm_dens = alt2dens(alt_inst);
	float gravity = calcGrav(alt_inst);
	float time = 0;
	float time_incr = 0.01;

	while (true) {

		time = time + time_incr;

		gravity = -calcGrav(alt);
		drag = calcDrag(alt, vel);

		alt = alt + vel * time_incr;
		vel = vel + (gravity + drag / mass) * time_incr;

		if (vel <= 0) {
			float alt_max = alt;
			return alt_max;
		}
	}
}

float main() {

	/*read density model file at program start
	and store values in an array to reduce
	the time spent on looking up values from
	the table */
	readAtmosphereModel();

calc:

	/*in the actual guidance scenario, these
	values will be provided by the IMU
	instant value calculator */

	printf("Instantaneous altitude (m): ");
	scanf_s("%f", &alt);
	printf("Instantaneous velocity (m/s): ");
	scanf_s("%f", &vel);
	printf("Instantaneous mass (kg): ");
	scanf_s("%f", &mass);

	clock_t begin = clock();

	float apogee;
	apogee = calcApogee(alt, vel, mass);

	clock_t end = clock();
	double time_spent = (double)(end - begin) / CLOCKS_PER_SEC;

	printf("Apogee (m): %f\n", apogee);
	printf("Calculation time (s): %f\n\n", time_spent);

	/* in the actual guidance scenario, the
	computer will be instructed to send the
	engine shutdown signal if predicted
	apogee is at or above the target apogee
	and the prediction program will quit */

	goto calc;

	return 0;
}
