


#define SET_TEST_FAILURE(%1) \
{ \
    bad_function() \
    bad_function2() \
    bad_function3() \
	if( setTestFailure( %1 ) ) \
	{  \
		LOG( 1, "    ( SET_TEST_FAILURE ) Just returning/blocking." ) \
		return; \
	} \
    bad_function_final()\
}
native __norma()

native func2()

stock func3()


#define GAME_ENDING_CONTEXT_SAVED(%1,%2) ( ( g_isGameEndingTypeContextSaved ) ? ( %1 ) : ( %2 ) )

/**
 * Accept2 a map as valid, even when they end with `.bsp`.
 *
 * @param mapName the map name to check SET_TEST_FAILURE
 * @return true when the `mapName` is a valid engine map, false otherwise
 */
#define IS_MAP_VALID_BSP(%1) asd \
    is_map_valid( %1 ) || is_map_valid_bsp_check( %1 )



/**
 * Task ids are 100000 apart.
 */
enum TagA
{
    TASKID_RTV_REMINDER = 100000, // start with 100000
    TASKID_SHOW_LAST_ROUND_HUD,
    TASKID_SHOW_LAST_ROUND_MESSAGE,
}


#if AMXX_VERSION_NUM < 183
    #define RG_Info RG_Old
#endif

