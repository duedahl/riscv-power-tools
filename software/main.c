/** Program for measuring BEEBS programs on Chipwhisperer targets
The program can be called from Chipwhisper jupyter by using "target.simpleserial_write('1', 'DUMMY')".
Here, '1' indicates which command should be executed (only 1 available currently) and 'DUMMY' is just some encoded char.

To get printouts, the DEBUG parameter can be set to 1, to remove - set to 0.

*/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "hal.h"
#include "simpleserial.h"

#define DEBUG 1

// Used to preserve memory layout and bypassing loop for Spike tracing //
#ifndef SPIKE 
#define SPIKE 0
#endif

void debug_print(char *c)
{
	if (DEBUG)
	{
	  do {
		putch(*c);

	  } while (*++c);
	}	
}


uint8_t perform_function(uint8_t* selection, uint8_t len)
{
  trigger_high();
	execute_cw();
	trigger_low();
	debug_print("OK!");
	return 0;
}

// Global variable - make it volatile so compiler doesn't optimize it out
volatile int debug_skip_loop = 0; // Needed to skip while loop during debugging

int main() 
{
    platform_init();
    init_uart();
    trigger_setup();
    debug_print("Starting\n");

#if SPIKE == 1
    if (debug_skip_loop) {
        simpleserial_addcmd('1', 1, perform_function);
        while(1)
            simpleserial_get();
    } else {
        uint8_t dummy = 'A';
        perform_function(&dummy, 1);
    }
#else
    if (debug_skip_loop) {
        uint8_t dummy = 'A';
        perform_function(&dummy, 1);
    } else {
        simpleserial_addcmd('1', 1, perform_function);
        while(1)
            simpleserial_get();
    }
#endif
}

