#!/usr/bin/env python
# # ==================================================================================
#   File:   createdb.py
#   Author: Larry W Jordan Jr (larouex@larouex.com)
#   Use:    Creates a Recipe Database for a new Fermentation Recipe Lifecycle
#
#   https://github.com/Larouex/open-fermentation-project
#
#   (c) 2022 Larouex Software Design LLC
#   This code is licensed under GNU license (see LICENSE.txt for details)
# ==================================================================================
import getopt, sys, time, string, threading, asyncio, os
from datetime import datetime, date
from distutils.command.config import config
from decimal import *
from gettext import NullTranslations
import logging as Log
import sqlite3
from sqlite3 import Error

# Our classes
from classes.config import Config
from classes.recipes import Recipes
from classes.currentrecipe import CurrentRecipe
from classes.printheader import PrintHeader

# -------------------------------------------------------------------------------
#   Function:   create_connection
#   Usage:      Create connection helper
# -------------------------------------------------------------------------------
def create_connection(db_file):

    conn = None

    try:
        conn = sqlite3.connect(db_file)
        return conn

    except Error as e:
        print("Exception::createdb.py(create_connection)->", e)

    return conn


# -------------------------------------------------------------------------------
#   Function:   create_table
#   Usage:      Create table helper
# -------------------------------------------------------------------------------
def create_table(conn, create_table_sql):

    try:
        c = conn.cursor()
        c.execute(create_table_sql)

    except Error as e:
        print("Exception::createdb.py(create_table)->", e)

    return


# -------------------------------------------------------------------------------
#   Function:   create_tracking
#   Usage:      Inserts the recipe checkpoints into the database
# -------------------------------------------------------------------------------
def create_tracking(conn, task):

    try:

        sql = """ INSERT INTO tracking(
                    recipe_phase,
                    recipe_hour,
                    completeness,
                    started_datetime,
                    completed_datetime,
                    temperature_format,
                    temperature_desired,
                    temperature_variance,
                    temperature_run_time,
                    temperature_idle_time,
                    humidity_desired,
                    humidity_variance,
                    humidity_run_time,
                    humidity_idle_time)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) """
        # 1,2,3,4,5,6,7,8,9,0,1,2,3,4
        cur = conn.cursor()
        cur.execute(sql, task)
        conn.commit()

        return cur.lastrowid

    except Exception as e:
        print("Exception::createdb.py(create_tracking)->", e)
        return None


# -------------------------------------------------------------------------------
#   Function:   get_tracking_table_definition
#   Usage:      Tracking Table Definition
# -------------------------------------------------------------------------------
def get_tracking_table_definition():
    sql_table_description = """ CREATE TABLE IF NOT EXISTS tracking (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    recipe_phase TEXT NOT NULL,
                                    recipe_hour INTEGER NOT NULL,
                                    completeness TEXT NOT NULL,
                                    started_datetime TEXT NULL,
                                    completed_datetime TEXT NULL,
                                    temperature_format TEXT NULL,
                                    temperature_desired INTEGER NOT NULL,
                                    temperature_variance INTEGER NOT NULL,
                                    temperature_run_time INTEGER NOT NULL,
                                    temperature_idle_time INTEGER NOT NULL,
                                    humidity_desired INTEGER NOT NULL,
                                    humidity_variance INTEGER NOT NULL,
                                    humidity_run_time INTEGER NOT NULL,
                                    humidity_idle_time INTEGER NOT NULL
                                ); """
    return sql_table_description


# -------------------------------------------------------------------------------
#   Function:   get_audit_table_definition
#   Usage:      Audit Table Definition
# -------------------------------------------------------------------------------
def get_audit_table_definition():
    sql_table_description = """ CREATE TABLE IF NOT EXISTS audit (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    recipe_phase TEXT NOT NULL,
                                    recipe_hour INTEGER NOT NULL,
                                    event_datetime TEXT NOT NULL,
                                    event_type TEXT NOT NULL,
                                    event_description TEXT NOT NULL
                                ); """
    return sql_table_description


# -------------------------------------------------------------------------------
#   Function:   get_relay_table_definition
#   Usage:      Audit Table Definition
# -------------------------------------------------------------------------------
def get_relay_table_definition():
    sql_table_description = """ CREATE TABLE IF NOT EXISTS relay (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    recipe_phase TEXT NOT NULL,
                                    recipe_hour INTEGER NOT NULL,
                                    event_datetime TEXT NOT NULL,
                                    event_type TEXT NOT NULL,
                                    event_description TEXT NOT NULL
                                ); """
    return sql_table_description


# -------------------------------------------------------------------------------
#   Function:   audit_event
#   Usage:      Insert Audit event into the database
# -------------------------------------------------------------------------------
def audit_event(conn, task):

    try:

        sql = """ INSERT INTO audit(
                    recipe_phase,
                    recipe_hour,
                    event_datetime,
                    event_type,
                    event_description)
                VALUES(?,?,?,?,?) """

        cur = conn.cursor()
        cur.execute(sql, task)
        conn.commit()

        return cur.lastrowid

    except Exception as e:
        print("Exception::createdb.py(audit_event)->", e)
        return None


# -------------------------------------------------------------------------------
#   main()
# -------------------------------------------------------------------------------
async def main(argv):

    # get desired options from the passed command line args
    verbose = False
    recipe_name = None
    short_options = "hvdr:"
    long_options = ["help", "verbose", "debug", "recipename="]
    full_cmd_arguments = sys.argv
    argument_list = full_cmd_arguments[1:]

    try:
        arguments, values = getopt.getopt(argument_list, short_options, long_options)
    except getopt.error as err:
        print("ERROR::createdb.py(main)->", str(err))

    for current_argument, current_value in arguments:

        if current_argument in ("-h", "--help"):
            print(
                "------------------------------------------------------------------------------------------------------------------------------------------"
            )
            print("HELP for createdb.py")
            print(
                "------------------------------------------------------------------------------------------------------------------------------------------"
            )
            print("")
            print("  BASIC PARAMETERS...")
            print("")
            print("  -h or --help - Print out this Help Information")
            print(
                "  -v or --verbose - Debug Mode with lots of Data will be Output to Assist with Debugging"
            )
            print(
                "  -d or --debug - Debug Mode with lots of DEBUG Data will be Output to Assist with Tracing and Debugging"
            )
            print("")
            print("  REQUIRED PARAMETERS...")
            print("")
            print("    -r or --recipename - The name provided must exist in the file named: recipes.json and is part of the")
            print("                          arrays of recipes that can be defined.")
            print("       USAGE: -r 'Salumi Toscano'")
            print("       USAGE: --recipename 'Salumi Toscano'")
            print("       DEFAULT: N/A, script will fail if not provided.")
            print("")
            print(
                "------------------------------------------------------------------------------------------------------------------------------------------"
            )
            return

        if current_argument in ("-v", "--verbose"):
            verbose = True
            Log.basicConfig(format="%(levelname)s: %(message)s", level=Log.INFO)
            Log.info("Verbose Logging Mode...")
        else:
            Log.basicConfig(format="%(levelname)s: %(message)s")

        if current_argument in ("-d", "--debug"):
            Log.basicConfig(format="%(levelname)s: %(message)s", level=Log.DEBUG)
            Log.info("Debug Logging Mode...")
        else:
            Log.basicConfig(format="%(levelname)s: %(message)s")

        if current_argument in ("-r", "--recipename"):
            recipe_name = current_value
            Log.info("Recipe name is specified as: {recipename}".format(recipename = recipe_name))
        else:
            # Missing Recipe Name. It is required, so fail
            print("[ERROR] -r --recipename must be specified and match a recipe name in recipes.json.")
            return

    logger = Log

    # Messaging
    print_header = PrintHeader(logger, verbose)

    # Load the configuration file
    config = Config(logger)
    config_data = config.data

    # Get the recipes array from the recipes.json file
    recipes = Recipes(logger)
    recipe_data = recipes.data

    # validate names and file naming pattern
    existing_recipe = [x for x in recipe_data["Name"] if x["Name"] == recipe_name]
    if len(existing_device) == 0:
        # Missing Recipe Name in recipes.json. It is required, so fail
        print("[ERROR] -r --recipename must match a recipe name in recipes.json.")
        return
    
    # create the file name
    active_recipe_file_name =  active_recipe_name_pattern.format(recipe_name)
    print_header.print(__file__, "Main", "active_recipe_file_name {active_recipe_file_name}".format(active_recipe_file_name))

    # Database - Create file name
    current_date_and_time = datetime.now()
    current_date_and_time_string = str(current_date_and_time)

    # Load the currentrecipe file
    current_recipe = CurrentRecipe(logger, True)
    current_recipe_data = current_recipe.data

    # create con object to connect
    root_directory = os.path.dirname(os.path.abspath(__file__))
    print("Root Directory:", root_directory)
    database_location = root_directory + "//" + active_recipe_file_name
    print("Database Location:", database_location)
    conn = create_connection(database_location)

    if conn is not None:
        # create tracking table
        create_table(conn, get_tracking_table_definition())

        # create audit table
        create_table(conn, get_audit_table_definition())

    else:
        print("Error! cannot create the database connection.")

    # Register completion Audit Event
    audit_event_1 = (
        "DATABASE",
        0,
        datetime.now(),
        "CREATED",
        "Completed Database Creation.",
    )
    audit_event(conn, audit_event_1)


    # init the values
    completeness = 0
    recipe_hour = 1

    # Lets Populate the Checkpoint Activities
    for recipe in recipe_cache_data:
        if recipe["Name"] == "Salumi Toscano":

            print("-------------------------------------------------------")
            print("Found Recipe...")

            # Gather Times and Build Up Meta Data
            incubate_toggle = recipe["Incubate"]["Cycle Time Toggle"]
            incubate_time = recipe["Incubate"]["Cycle Time"]
            cure_toggle = recipe["Cure"]["Cycle Time Toggle"]
            cure_time = recipe["Cure"]["Cycle Time"]
            finish_toggle = recipe["Finish"]["Cycle Time Toggle"]
            finish_time = recipe["Finish"]["Cycle Time"]

            # create loop numbers
            incubate_loop = (incubate_toggle * incubate_time) - 1
            cure_loop = (cure_toggle * cure_time) - 1
            finish_loop = (finish_toggle * finish_time) - 1

            # Completeness - Based on all hours, percent of 100
            completeness_value = Decimal(
                100 / (incubate_loop + cure_loop + finish_loop)
            )

            print(" Completeness=", completeness_value)

            # Incubate
            print(" Creating Incubation Lifecycle...")
            for x in range(0, incubate_loop):
                tracking_incubation = (
                    "Incubate",
                    recipe_hour,
                    str(completeness_value),
                    None,
                    None,
                    "F",
                    recipe["Incubate"]["Temperature"]["Desired"],
                    recipe["Incubate"]["Temperature"]["Variance"],
                    recipe["Incubate"]["Temperature"]["Run Time"],
                    recipe["Incubate"]["Temperature"]["Idle Time"],
                    recipe["Incubate"]["Humidity"]["Desired"],
                    recipe["Incubate"]["Humidity"]["Variance"],
                    recipe["Incubate"]["Humidity"]["Run Time"],
                    recipe["Incubate"]["Humidity"]["Idle Time"],
                )
                create_tracking(conn, tracking_incubation)
                recipe_hour = recipe_hour + 1

            # Cure
            print(" Creating Cure Lifecycle...")
            for x in range(0, cure_loop):
                tracking_cure = (
                    "Cure",
                    recipe_hour,
                    str(completeness_value),
                    None,
                    None,
                    "F",
                    recipe["Cure"]["Temperature"]["Desired"],
                    recipe["Cure"]["Temperature"]["Variance"],
                    recipe["Cure"]["Temperature"]["Run Time"],
                    recipe["Cure"]["Temperature"]["Idle Time"],
                    recipe["Cure"]["Humidity"]["Desired"],
                    recipe["Cure"]["Humidity"]["Variance"],
                    recipe["Cure"]["Humidity"]["Run Time"],
                    recipe["Cure"]["Humidity"]["Idle Time"],
                )
                create_tracking(conn, tracking_cure)
                recipe_hour = recipe_hour + 1

            # Finish
            print(" Creating Finish Lifecycle...")
            for x in range(0, finish_loop):
                completeness = 1
                tracking_finish = (
                    "Finish",
                    recipe_hour,
                    str(completeness_value),
                    None,
                    None,
                    "F",
                    recipe["Finish"]["Temperature"]["Desired"],
                    recipe["Finish"]["Temperature"]["Variance"],
                    recipe["Finish"]["Temperature"]["Run Time"],
                    recipe["Finish"]["Temperature"]["Idle Time"],
                    recipe["Finish"]["Humidity"]["Desired"],
                    recipe["Finish"]["Humidity"]["Variance"],
                    recipe["Finish"]["Humidity"]["Run Time"],
                    recipe["Finish"]["Humidity"]["Idle Time"],
                )
                create_tracking(conn, tracking_finish)
                recipe_hour = recipe_hour + 1

        # Register completion Audit Event
        audit_event_2 = (
            "CREATE",
            0,
            datetime.now(),
            "TRACKING",
            "Completed Recipe Tracking Insertion of all Checklpoints into the Database.",
        )
        audit_event(conn, audit_event_2)

        print("Completed!")
        print("-------------------------------------------------------")

        break
    else:
        index = index + 1


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))