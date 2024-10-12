/*********************************
   *** Debug Utility By Destro ***

- Activar:
#define DEBUG_ENABLE

- Configuracion opcional:

// Si el nivel es menor al numero de la función (debug_console1/2/3() y debug_log1/2/3()), se comporta como debug_hidden()
#define DEBUG_LEVEL 3				// default: 3

// Números de registros que se muestran al usar debug_end()
#define DEBUG_MAX_RECORDS			// defaukt: 20

#define DEBUG_ENABLE_GAMETIME		// Agrega el gametime al mensaje
#define DEBUG_ENABLE_CLIENT			// Los mensajes tambien se muestran a todos los jugadores
#define DEBUG_ONLY_CONSOLE			// debug_log() y debug_hidden() funcionan como debug_console()
#define DEBUG_ONLY_LOGS				// debug_console() y debug_hidden() funcionan como debug_log()
#define DEBUG_HIDDEN_ALL			// debug_log() y debug_console() funcionan como debug_hidden()
#define DEBUG_LOGFILE "debug.log"	// Define el nombre del archivo Log, si no se define usa "debug_%PLUGIN%.log"


- Funciones (funciones falsa):
# Inicializa variables, usar en plugin_init/precache()
@ debug_init()

# Guarda en el Log los ultimos registros
@ debug_end()

# Muestra mensaje en la consola del servidor
@ debug_console1(info[], any:...)
@ debug_console2(info[], any:...)
@ debug_console3(info[], any:...)

# Muestra mensaje en la consola del servidor y tambien lo guarda en Log
@ debug_log1(info[], any:...)
@ debug_log2(info[], any:...)
@ debug_log3(info[], any:...)
	
# No muestra mensaje, solo se puede ver al utilizar debug_end()
@ debug_hidden(info[], any:...)

# Calcula los milisegundos entre Start y End
@ debug_performance_start(keyname)
@ debug_performance_end(keyname, info[], any:...) 

***********************************************************************/

/* AMXX Editor 3.0 */
/*@fakefunc: debug_console1(const fmt[], any:...)*/
/*@fakefunc: debug_console2(const fmt[], any:...)*/
/*@fakefunc: debug_console3(const fmt[], any:...)*/

/*@fakefunc: debug_log1(const fmt[], any:...)*/
/*@fakefunc: debug_log2(const fmt[], any:...)*/
/*@fakefunc: debug_log3(const fmt[], any:...)*/
/*@fakefunc: debug_hidden(const fmt[], any:...)*/

#if defined _debug_included
  #endinput
#endif
#define _debug_included

#if !defined DEBUG_LEVEL
	#define DEBUG_LEVEL 3
#endif

#if !defined DEBUG_MAX_RECORDS
	#define DEBUG_MAX_RECORDS 20
#endif

#define DEBUG_DRAW_NONE    0
#define DEBUG_DRAW_CONSOLE 1
#define DEBUG_DRAW_LOG	   2

#if defined DEBUG_ENABLE
	#define __DEBUG_BUFF			256
	#define __DEBUG_MAXLINES		500

	stock __debug_list[DEBUG_MAX_RECORDS][__DEBUG_BUFF], Float:__debug_list_gametime[DEBUG_MAX_RECORDS]
	stock __debug_list_loop, __debug_list_size, Float:__debug_gametime, Float:__debug_performancetime
	stock __debug_logfile[64], __debug_amxxfile[32], __debug_mapname[32], __debug_date[32]

	#if defined DEBUG_ONLY_CONSOLE
		#define debug_console1(%1) __debug(DEBUG_DRAW_CONSOLE,1,%1)
		#define debug_console2(%1) __debug(DEBUG_DRAW_CONSOLE,2,%1)
		#define debug_console3(%1) __debug(DEBUG_DRAW_CONSOLE,3,%1)
		#define debug_log1(%1) __debug(DEBUG_DRAW_CONSOLE,1,%1)
		#define debug_log2(%1) __debug(DEBUG_DRAW_CONSOLE,2,%1)
		#define debug_log3(%1) __debug(DEBUG_DRAW_CONSOLE,3,%1)
		#define debug_hidden(%1) __debug(DEBUG_DRAW_CONSOLE,1,%1)

	#else
	#if defined DEBUG_ONLY_LOGS

		#define debug_console1(%1) __debug(DEBUG_DRAW_LOG,1,%1)
		#define debug_console2(%1) __debug(DEBUG_DRAW_LOG,2,%1)
		#define debug_console3(%1) __debug(DEBUG_DRAW_LOG,3,%1)
		#define debug_log1(%1) __debug(DEBUG_DRAW_LOG,1,%1)
		#define debug_log2(%1) __debug(DEBUG_DRAW_LOG,2,%1)
		#define debug_log3(%1) __debug(DEBUG_DRAW_LOG,3,%1)
		#define debug_hidden(%1) __debug(DEBUG_DRAW_LOG,1,%1)

	#else
	#if defined DEBUG_HIDDEN_ALL

		#define debug_console1(%1) __debug(DEBUG_DRAW_NONE,1,%1)
		#define debug_console2(%1) __debug(DEBUG_DRAW_NONE,2,%1)
		#define debug_console3(%1) __debug(DEBUG_DRAW_NONE,3,%1)
		#define debug_log1(%1) __debug(DEBUG_DRAW_NONE,1,%1)
		#define debug_log2(%1) __debug(DEBUG_DRAW_NONE,2,%1)
		#define debug_log3(%1) __debug(DEBUG_DRAW_NONE,3,%1)	
		#define debug_hidden(%1) __debug(DEBUG_DRAW_NONE,1,%1)
				
	#else

		#define debug_console1(%1) __debug(DEBUG_DRAW_CONSOLE,1,%1)
		#define debug_console2(%1) __debug(DEBUG_DRAW_CONSOLE,2,%1)
		#define debug_console3(%1) __debug(DEBUG_DRAW_CONSOLE,3,%1)
		#define debug_log1(%1) __debug(DEBUG_DRAW_LOG,1,%1)
		#define debug_log2(%1) __debug(DEBUG_DRAW_LOG,2,%1)
		#define debug_log3(%1) __debug(DEBUG_DRAW_LOG,3,%1)
		#define debug_hidden(%1) __debug(DEBUG_DRAW_NONE,1,%1)

	#endif
	#endif
	#endif
	

	#define debug_performance_start(%1) \
	new __debug_tick_%1 = tickcount()
	
	#define debug_performance_end(%1,%2) \
	__debug_log_write("[DEBUG Performance] ^"%s^" -> (%dms)",%2,tickcount()-__debug_tick_%1)

	#define __debug_check_init() if(!__debug_amxxfile[0]) debug_init()
	
	stock debug_init()
	{
		get_plugin(-1, __debug_amxxfile, 31)
		replace(__debug_amxxfile, 31, ".amxx", "")

		get_mapname(__debug_mapname, 31)
		
		get_localinfo("amxx_logs", __debug_logfile, 63)
		#if defined DEBUG_LOGFILE
		format(__debug_logfile, 63 "%s/%s", __debug_logfile, DEBUG_LOGFILE)
		#else
		format(__debug_logfile, 63, "%s/debug_%s.log", __debug_logfile, __debug_amxxfile)
		#endif
		
		__debug_update_date()
		__debug_log_write("[DEBUG START: %s] - Map: ^"%s^"  |  Plugin: ^"%s^"", __debug_date, __debug_mapname, __debug_amxxfile)
	}

	stock debug_end()
	{
		__debug_check_init()
		
		__debug_gametime = get_gametime()
		
		__debug_update_date()
		__debug_log_write("[DEBUG END:  %s] - Map: ^"%s^"  |  Plugin: ^"%s^"", __debug_date, __debug_mapname, __debug_amxxfile)
		
		if(__debug_list_size == 0)
		{
			__debug_log_write("# [ Empty Records List ]")
			__debug_log_write("----------------------------------------------------------------------^n")
			return
		}
		
		new Float:last_gametime, slot

		slot = __debug_list_loop - 1
		if(slot < 0) slot += __debug_list_size
		
		last_gametime = __debug_list_gametime[slot]
		
		__debug_log_write("# - GameTime: (%.4f)  |  Last: (%.4f)  |  Difference: (%dms)", __debug_gametime, last_gametime, floatround((__debug_gametime - last_gametime) * 1000.0))
		__debug_log_write("# - Records List:")

		for(new count=__debug_list_size; count > 0; count--)
		{
			slot = __debug_list_loop - count
			if(slot < 0) slot += __debug_list_size

			if(__debug_gametime == __debug_list_gametime[slot])
				__debug_log_write("#%2d:  (curframe) - [%s]", count, __debug_list[slot])
			else
				__debug_log_write("#%2d:  (%dms) - [%s]", count, floatround((__debug_gametime - __debug_list_gametime[slot]) * 1000.0), __debug_list[slot])
		}
	
		__debug_log_write("----------------------------------------------------------------------^n")
	}
	
	stock __debug(drawmode, level, const info[], any:...)
	{
		static slot
		if(__debug_list_size == DEBUG_MAX_RECORDS)
		{
			slot = __debug_list_loop++
			__debug_list_loop = __debug_list_loop % DEBUG_MAX_RECORDS
		}
		else	slot = __debug_list_size++
	
		vformat(__debug_list[slot], __DEBUG_BUFF-1, info, 4)
		__debug_list_gametime[slot] = __debug_gametime = get_gametime()
		
		if(drawmode == DEBUG_DRAW_NONE || level > DEBUG_LEVEL)
			return

		#if defined DEBUG_ENABLE_CLIENT
			client_print(0, print_console, "[DEBUG, GameTime: (%.3f)] %s", __debug_gametime, __debug_list[slot])
		#endif

		if(drawmode == DEBUG_DRAW_CONSOLE)
		{
			#if defined DEBUG_GAMETIME
				server_print("[DEBUG, GameTime: (%.3f)] %s", __debug_gametime, __debug_list[slot])
				#if defined DEBUG_ENABLE_CLIENT
					client_print(0, print_console, "[DEBUG, GameTime: (%.3f)] %s", __debug_gametime, __debug_list[slot])
				#endif
			#else
				server_print("[DEBUG] %s", __debug_list[slot])
				#if defined DEBUG_ENABLE_CLIENT
					client_print(0, print_console, "[DEBUG] %s", __debug_list[slot])
				#endif
			#endif
		}
		else
		{
			#if defined DEBUG_GAMETIME
				__debug_log_write("[DEBUG, GameTime: (%.3f)] %s", __debug_gametime, __debug_list[slot])
			#else
				__debug_log_write("[DEBUG] %s", __debug_list[slot])
			#endif
		}
	}
			
	stock __debug_update_date()
	{
		get_time("%d/%m/%Y - %H:%M:%S", __debug_date, 31)
	}

	stock __debug_log_clear()
	{
		__debug_check_init()

		delete_file(__debug_logfile)

		__debug_update_date()
		__debug_log_write("[DEBUG CLEAR: %s] - Map: ^"%s^"  |  Plugin: ^"%s^"", __debug_date, __debug_mapname, __debug_amxxfile)
	}
	
	stock __debug_log_write(const info[], any:...)
	{
		__debug_check_init()
		
		static buff[__DEBUG_BUFF], lines
		
		if(++lines > __DEBUG_MAXLINES)
		{
			lines = 0
			__debug_log_clear()
		}
		
	
		vformat(buff, charsmax(buff), info, 2)

		write_file(__debug_logfile, buff)
		server_print(buff)

		#if defined DEBUG_ENABLE_CLIENT
			client_print(0, print_console, buff)
		#endif
	}

#else

	#define debug_init(%1) {}
	#define debug_end(%1) {}
	
	#define debug_console1(%1) {}
	#define debug_console2(%1) {}
	#define debug_console3(%1) {}
	
	#define debug_log1(%1) {}
	#define debug_log2(%1) {}
	#define debug_log3(%1) {}
	
	#define debug_hidden(%1) {}
	
	#define debug_performance_start(%1) {}
	#define debug_performance_end(%1) {}

	#define __debug(%1) {}

#endif

