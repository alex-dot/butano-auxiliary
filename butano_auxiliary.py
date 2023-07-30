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
    argparser.add_argument('--no-mnimization',dest='prevent_minimization',action='store_true',
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
        maps = json.load(maps_json)
        if not config.PREVENT_TILEMAP_MINIMIZATION:
            used_tiles = get_used_tiles(maps)
            for ut in used_tiles:
                create_tilemap(ut["image_file_name"],ut["image_src"])
            for tilemap in maps:
                tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,tilesize,image_file_name,image_src = open_map(tilemap)
                bitmap,tilemap_width = get_bitmap(image_file_name)
                create_map_data(tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,image_file_name,tilesize,used_tiles,bitmap,tilemap_width)
        else:
            for tilemap in maps:
                tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,tilesize,image_file_name,image_src = open_map(tilemap)
                bitmap,tilemap_width = create_tilemap(image_file_name,image_src)
                create_map_data(tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,image_file_name,tilesize,used_tiles,bitmap,tilemap_width)

    if config.CREATE_GLOBALS_FILE:
        create_tilemap_globals_file()

    print("Finished")
