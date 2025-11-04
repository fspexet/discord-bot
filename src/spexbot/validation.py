def is_valid_snowflake(snowflake_id: int) -> bool:
    """
    Validate a Discord Snowflake ID.
    
    ## Parameters
    
    - `snowflake_id` Snowflake ID to be validated.

    ## Returns

    Retruns `True` if the ID is a valid Discord Snowflake ID. Otherwise `False`.
    """
    # Must be positive
    if snowflake_id < 0:
        return False
    
    # Must fit in 64 bits (unsigned)
    if snowflake_id >= 2**64:
        return False
    
    # Discord epoch: January 1, 2015 (in milliseconds)
    DISCORD_EPOCH = 1420070400000
    
    # Extract timestamp (first 42 bits)
    timestamp_ms = (snowflake_id >> 22) + DISCORD_EPOCH
    
    # Check if timestamp is reasonable (not before Discord epoch)
    if timestamp_ms < DISCORD_EPOCH:
        return False
    
    # Check if timestamp is not in the future (with small buffer for clock skew)
    import time
    current_time_ms = int(time.time() * 1000)
    if timestamp_ms > current_time_ms + 60000:  # 1 minute buffer
        return False
    
    return True