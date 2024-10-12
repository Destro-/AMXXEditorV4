#if defined _crxranks_included
    #endinput
#endif

#define _crxranks_included

#if !defined _crxranks_const_included
    #include <crxranks_const>
#endif

/**
 * Called when the client's level changes.
 *
 * @param id	 		Client index.
 * @param level 		New level.
 * @param levelup		True if the client gained a level, false if he lost one.
 * @noreturn
 */
forward crxranks_user_level_updated(id, level, bool:levelup)

/**
 * Called right before the client receives XP.
 *
 * @param id	 		Client index.
 * @param xp	 		Amount of XP ready to be received.
 * @param source	 	The XP source.
 * @return              CRXRANKS_STOP to prevent the XP from being added,
 *                      CRXRANKS_CONTINUE to let the XP pass through,
 *                      any integer value to modify the amount of XP that
 *                      is going to be received
 */
forward crxranks_user_receive_xp(id, xp, CRXRanks_XPSources:source)

/**
 * Called right after the client's XP amount changes.
 *
 * @param id	 		Client index.
 * @param xp	 		Amount of XP the client has after the change.
 * @param source	 	The XP source that caused the change.
 * @noreturn
 */
forward crxranks_user_xp_updated(id, xp, CRXRanks_XPSources:source)

/**
 * Returns the chat prefix set in the plugin's configuration file.
 *
 * @param buffer	 	Buffer to store the prefix in.
 * @param len 			Maximum buffer length.
 * @noreturn
 */
native crxranks_get_chat_prefix(buffer[], len)

/**
 * Returns the flags that clients will receive when they reach the final level.
 *
 * @param buffer	 	Buffer to store the flags in.
 * @param len 			Maximum buffer length.
 * @return				Flags as bit value.
 */
native crxranks_get_final_flags(buffer[] = "", len = 0)

/**
 * Returns the HUD info format set in the plugin's configuration file.
 *
 * @param final		 	If true, it will get the HUD_FORMAT_FINAL settings, otherwise HUD_FORMAT if false.
 * @param buffer	 	Buffer to store the HUD info format in.
 * @param len 			Maximum buffer length.
 * @noreturn
 */
native crxranks_get_hudinfo_format(bool:final, buffer[], len)

/**
 * Returns the number of available levels.
 *
 * @return				Number of available levels.
 */
native crxranks_get_max_levels()

/**
 * Searches for a rank name by a specific level number.
 *
 * @param level	 		Level number.
 * @param buffer	 	Buffer to store the rank name in.
 * @param len 			Maximum buffer length.
 * @return				0 if the level number is out of range, 1 otherwise.
 */
native crxranks_get_rank_by_level(level, buffer[], len)

/**
 * Returns the data saving type set in the plugin's configuration file.
 *
 * @note You can use the constants CRXRANKS_ST_NICKNAME, CRXRANKS_ST_IP
 *		 and CRXRANKS_ST_STEAMID instead of numbers.
 *
 * @return				0 if it's set to nickname, 1 for IP and 2 for SteamID.
 */
native CRXRanks_SaveTypes:crxranks_get_save_type()

/**
 * Returns a key value set in the [Settings] section in the plugin's configuration file.
 *
 * @param key	 		Key to search for.
 * @param value 	 	Buffer to store the value in.
 * @param len 			Maximum buffer length.
 * @return				True if the key was found, false otherwise.
 */
native bool:crxranks_get_setting(key[], value[], len)

/**
 * Returns the client's HUD information.
 *
 * @param id		 	Client index.
 * @param buffer	 	Buffer to store the HUD information in.
 * @param len 			Maximum buffer length.
 * @noreturn
 */
native crxranks_get_user_hudinfo(id, buffer[], len)

/**
 * Returns the client's current level.
 *
 * @param id		 	Client index.
 * @return				Client's current level.
 */
native crxranks_get_user_level(id)

/**
 * Returns the client's next rank.
 *
 * @param id		 	Client index.
 * @param buffer	 	Buffer to store the rank name in.
 * @param len 			Maximum buffer length.
 * @noreturn
 */
native crxranks_get_user_next_rank(id, buffer[], len)

/**
 * Returns the XP needed for the client to reach the next level.
 *
 * @param id		 	Client index.
 * @return 				XP needed for the client to reach the next level.
 */
native crxranks_get_user_next_xp(id)

/**
 * Returns the client's current rank.
 *
 * @param id		 	Client index.
 * @param buffer	 	Buffer to store the rank name in.
 * @param len 			Maximum buffer length.
 * @noreturn
 */
native crxranks_get_user_rank(id, buffer[], len)

/**
 * Returns the amount of XP that the client has.
 *
 * @param id		 	Client index.
 * @return				Client's current XP.
 */
native crxranks_get_user_xp(id)

/**
 * Returns the vault name set in the plugin's configuration file.
 *
 * @param buffer	 	Buffer to store the vault name in.
 * @param len 			Maximum buffer length.
 * @noreturn
 */
native crxranks_get_vault_name(buffer[], len)

/**
 * Returns the VIP flags set in the plugin's configuration file.
 *
 * @param buffer	 	Buffer to store the flags in.
 * @param len 			Maximum buffer length.
 * @return				Flags as bit value.
 */
native crxranks_get_vip_flags(buffer[] = "", len = 0)

/**
 * Returns the amount of XP required for a specific level.
 *
 * @param level			Level number.
 * @return				-1 if the level is out of range, XP required for that level otherwise.
 */
native crxranks_get_xp_for_level(level)

/**
 * Returns the XP reward that the client will get in a specific sitaution.
 *
 * @param id		 	Client index.
 * @param reward		Reward keyword.
 * @return				XP reward that the client will get.
 */
native crxranks_get_xp_reward(id, reward[])

/**
 * Gives a specific amount of XP to the client.
 *
 * @note If the "reward" parameter is set, the plugin will ignore the amount set
 *       in the "amount" parameter and will attempt to give the XP set in the
 *		 configuration file by the specific keyword set in the "reward" parameter.
 *
 * @param id		 	Client index.
 * @param amount		XP amount.
 * @param reward		Reward keyword.
 * @param source		XP source.
 * @return				Amount of XP given.
 */
native crxranks_give_user_xp(id, amount = 0, reward[] = "", CRXRanks_XPSources:source = CRXRANKS_XPS_PLUGIN)

/**
 * Checks if the client has HUD information enabled.
 *
 * @param id			Client index.
 * @return				True if he has, false otherwise.
 */
native bool:crxranks_has_user_hudinfo(id)

/**
 * Checks if the HUD info system is using DHUD messages.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_hi_using_dhud()

/**
 * Checks if the HUD information system is enabled.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_hud_enabled()

/**
 * Checks if the screen fade when a client loses a level is enabled.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_sfdn_enabled()

/**
 * Checks if the screen fade when a client gains a level is enabled.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_sfup_enabled()

/**
 * Checks if the client is on the final level.
 *
 * @param id			Client index.
 * @return				True if he is, false otherwise.
 */
native bool:crxranks_is_user_on_final(id)

/**
 * Checks if the client is VIP according to the VIP flags set in the plugin's configuration file.
 *
 * @param id			Client index.
 * @return				True if he is, false otherwise.
 */
native bool:crxranks_is_user_vip(id)

/**
 * Checks if the plugin is using MySQL to save/load XP.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_using_mysql()

/**
 * Checks if the XP notifier system is enabled.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_xpn_enabled()

/**
 * Checks if the XP notifier system is using DHUD messages.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_is_xpn_using_dhud()

/**
 * Sets the exact amount of XP that th client has.
 *
 * @param id		 	Client index.
 * @param amount		XP amount.
 * @param source		XP source.
 * @return				Amount of XP given.
 */
native crxranks_set_user_xp(id, amount, CRXRanks_XPSources:source = CRXRANKS_XPS_PLUGIN)

/**
 * Checks if the plugin's option to use combined events is enabled.
 *
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_using_combined_events()

/**
 * Checks whether the specified XP reward is set in the configuration file.
 *
 * @param reward		The XP reward to check.
 * @return				True if it is, false otherwise.
 */
native bool:crxranks_xp_reward_is_set(reward[])