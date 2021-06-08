.386
.model flat, stdcall
.stack 4096
ExitProcess PROTO, dwExitCode: DWORD

; THIS PROGRAM IS FOR x86 WINDOWS DEMONSTRATION
; WOULD NEED CONVERSION BETWEEN ARCHITECTURES FOR USE
; WORK-IN-PROGRESS

.data

	; 100000 = 1 for demo convenience reasons

	vel			SDWORD	100000
	alt			SDWORD	100000
	time		SDWORD	1000
	accel		SDWORD	500000

	;dcoeff		SDWORD	40000
	;csarea		SDWORD	09600

.code

main PROC

; register maid service
	mov		eax, 0
	mov		ebx, eax
	mov		ecx, ebx
	mov		edx, ecx

nextstep:
	mov		eax, accel    ; get acceleration (500 for test purposes)
	mov		ebx, 1000
	div		ebx			  ; multiply by time increment
	mov		[accel], eax  ; get accel divided by time increment

	mov		eax, vel      
	mov		ebx, accel	  ; update velocity
	add		eax, ebx
	mov		[vel], eax    ; store velocity

	mov		eax, accel
	mov		ebx, 1000
	mul		ebx           ; restore real accel
	mov		[accel], eax  ; store real accel

	mov		eax, vel
	mov		ebx, 1000
	div		ebx
	mov		[vel], eax    ; get velocity divided by time increment

	mov		eax, alt
	mov		ebx, vel	  ; update altitude
	add		eax, ebx
	mov		[alt], eax    ; store altitude

	mov		eax, vel
	mov		ebx, 1000
	mul		ebx           ; restore real velocity
	mov		[vel], eax    ; store real velocity

	mov		eax, time
	add		eax, 10
	mov		[time], eax   ; update time by time increment

	; THIS PART IS ONLY FOR TESTING/DEBUG PURPOSES
	mov		eax, alt
	mov		ebx, vel
	mov		ecx, accel
	mov		edx, time

	; register maid service
	mov		eax, 0
	mov		ebx, eax
	mov		ecx, ebx
	mov		edx, ecx

	; in reality, we will keep going until vel is equal to or less than zero
	mov		eax, time
	cmp		eax, 6000
	jle		endsum
	jmp		nextstep

endsum:

	INVOKE ExitProcess, 0
main ENDP
END main
