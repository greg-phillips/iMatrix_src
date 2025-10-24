Create a detailed plan document to update the functionality of processing the dbc file. Each signal entry has a min and max value the we use for saving the min/max graph values. For hybrid sensors we need to define the maximum valid range to sampled data. to calculate this value look for the lowest state value for this signal and define a new stucture elemnet max_value that is used to compare the inbound data with to determine if the value is a state or sensor value. 



Create a detailed plan document to update the functionality of the routines in wrp_config.c to handle the storage of the states assocated with any stateful or hybrid sensors. the routines write_config, read_config and print_config need to support this functionality. The state value is all that needs to be stored. The number of entries and the states is the required addition. The states must be sorted numberically starting with the lowest value to highest value.
Create a detailed todo list document to follow and check off as each element is completed.
