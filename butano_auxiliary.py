#!/usr/bin/env python

"""tilemap_minimizer.py: Generate minimized tilemaps and butano-compatible map headers from tiled 
                         projects. This script assumes to be run from the root folder of a butano 
                         project."""

import os
import sys
import json
import math
import argparse
from xml.dom.minidom import parse as xmlparse
from numpy import subtract
from PIL import Image, ImageOps

import config
from tilemap_minimizer import *
from mapdata_generator import *

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate minimized tilemaps and butano-compatible map headers from tiled projects. 
            This script assumes to be run from the root folder of a butano project.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
    argparser.add_argument('--force-image-gen',dest='force_img',action='store_true',
                           help='Force tilemap image generation')
    argparser.add_argument('--force-map-gen',dest='force_map',action='store_true',
                           help='Force tilemap data generation')
    argparser.add_argument('-n','--namespace',dest='namespace',
                           help='Set namespace for project')
    argparser.add_argument('-o','--create-objects',dest='objects',action='store_true',
                           help='Parse all object layers (actors and boundaries)')
    argparser.add_argument('--create-actors',dest='actors',action='store_true',
                           help='Parse actor layer')
    argparser.add_argument('--create-boundaries',dest='boundaries',action='store_true',
                           help='Parse boundary layer')
    argparser.add_argument('-g','--globals',dest="globals",action='store_true',
                           help='Create globals file')
    args = argparser.parse_args()

    if args.force:
        config.FORCE_IMAGE_GENERATION = True
        config.FORCE_MAP_DATA_GENERATION = True
    if args.force_img:
        config.FORCE_IMAGE_GENERATION = True
    if args.force_map:
        config.FORCE_MAP_DATA_GENERATION = True
    if args.namespace:
        config.NAMESPACE = args.namespace
        config.NAMESPACE_UNDERSCORE = config.NAMESPACE + "_"
        config.NAMESPACE_COLON = config.NAMESPACE + "::"
    if args.objects:
        config.PARSE_ACTORS = True
        config.PARSE_BOUNDARIES = True
    if args.objects:
        config.PARSE_ACTORS = True
    if args.objects:
        config.PARSE_BOUNDARIES = True
    if args.globals:
        config.CREATE_GLOBALS_FILE = True

    with open("graphics/ressources/maps.json") as maps_json:
        maps = json.load(maps_json)
        for tilemap in maps:
            tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,bitmap,tilemap_width = create_map(tilemap)
            create_map_data(tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,bitmap,tilemap_width)

    if config.CREATE_GLOBALS_FILE:
        create_tilemap_globals_file()

    print("Finished")
