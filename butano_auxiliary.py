#!/usr/bin/env python

"""butano_auxiliary.py: Generate minimized tilemaps and butano-compatible map headers from tiled 
                        projects. """

import os
import sys
import json
import math
import argparse
from xml.dom.minidom import parse as xmlparse
from numpy import subtract
from PIL import Image, ImageOps

import config
from tilemap_compressor import *
from mapdata_generator import *
from tilemap_minimizer import *

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate minimized tilemaps and butano-compatible map headers from tiled projects. 
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
    argparser.add_argument('--force-image-gen',dest='force_img',action='store_true',
                           help='Force tilemap image generation')
    argparser.add_argument('--force-map-gen',dest='force_map',action='store_true',
                           help='Force tilemap data generation')
    argparser.add_argument('--map-file',dest='tmx_override',
                           help='Specifiy tiled TMX map, ignoring maps.json; requires --map-name')
    argparser.add_argument('--map-name',dest='map_name',
                           help='Specifiy map name, ignoring maps.json; requires --map-file')
    argparser.add_argument('--no-minimization',dest='prevent_minimization',action='store_true',
                           help='Do not minimize tilemap before compression')
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
    if ( args.tmx_override and not args.map_name ) or \
       ( not args.tmx_override and args.map_name ):
        print("If either --map-file or --map-name is set, the other must be set, too")
        sys.exit()
    if args.tmx_override:
        config.TMX_OVERRIDE = args.tmx_override.split('/')[-1]
        if not os.path.exists("graphics/ressources/" + config.TMX_OVERRIDE):
            print("Did not find a tiled map file: "+config.TMX_OVERRIDE)
            sys.exit()
    if args.map_name:
        config.MAP_NAME = args.map_name
    if args.prevent_minimization:
        config.PREVENT_TILEMAP_MINIMIZATION = True
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
        if config.TMX_OVERRIDE and config.MAP_NAME:
            maps = json.loads('[{"name":"'+config.MAP_NAME+'","tmx":"'+config.TMX_OVERRIDE+'"}]')
        else:
            maps = json.load(maps_json)
        if not config.PREVENT_TILEMAP_MINIMIZATION:
            map_data = get_used_tiles(maps)
            for mapdict in map_data:
                bitmap,tilemap_width = create_tilemap(mapdict)
                create_map_data(mapdict,bitmap,tilemap_width)
        else:
            for tilemap in maps:
                map_data = open_map(tilemap)
                bitmap,tilemap_width = create_tilemap(map_data[0])
                create_map_data(map_data[0],bitmap,tilemap_width)

    if config.CREATE_GLOBALS_FILE:
        create_tilemap_globals_file()

    print("Finished")
