#!/usr/bin/env python

"""butano_auxiliary.py: Generate minimized tilemaps and butano-compatible map headers from tiled 
                        projects. """

import os
import sys
import json
import argparse

import config
import tilemap_compressor as tc
import mapdata_generator as mg
import tilemap_minimizer as tm
from mapdata_models import MapObject

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
    argparser.add_argument('--force-instantiations',dest='force_insta',action='store_true',
                           help='Force foton class instantiation generation')
    argparser.add_argument('-s','--save-temp-files',dest='save_temp_imgs',action='store_true',
                           help="""Save temporary files (like *_minimized.bmp and *_combined.bmp
                                   and some json files)""")
    argparser.add_argument('--map-file',dest='tmx_override',
                           help='Specifiy tiled TMX map, ignoring foton.json; requires --map-name')
    argparser.add_argument('--map-name',dest='map_name',
                           help='Specifiy map name, ignoring foton.json; requires --map-file')
    argparser.add_argument('--no-minimization',dest='prevent_minimization',action='store_true',
                           help='Do not minimize tilemap before compression')
    argparser.add_argument('--no-map-consolidation',
                           dest='prevent_consolidation',action='store_true',
                           help="""Prevent consolidation of maps so each map will have their own
                                   generated tilemap""")
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
    argparser.add_argument('-a','--author',dest='author_name',
                           help='Author name to be put into copyright line.')
    argparser.add_argument('-m','--mail',dest='author_mail',
                           help='Author mail address to be put into copyright line.')
    argparser.add_argument('--header-line',dest='header_line',
                           help='Author name to be put into copyright line.')
    args = argparser.parse_args()

    if args.force:
        config.FORCE_IMAGE_GENERATION = True
        config.FORCE_MAP_DATA_GENERATION = True
        config.FORCE_INSTANTIATION_GENERATION = True
    if args.force_img:
        config.FORCE_IMAGE_GENERATION = True
    if args.force_map:
        config.FORCE_MAP_DATA_GENERATION = True
    if args.force_insta:
        config.FORCE_INSTANTIATION_GENERATION = True
    if args.save_temp_imgs:
        config.SAVE_TEMPORARY_FILES = True
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
    if args.prevent_consolidation:
        config.PREVENT_MAP_CONSOLIDATION = True
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
    if args.author_name:
        config.AUTHOR_NAME = args.author_name
    if args.author_mail:
        config.AUTHOR_MAIL = args.author_mail
    if args.header_line:
        config.FILE_HEADER = args.header_line

    with open("graphics/ressources/foton.json", encoding="utf-8") as foton_json:
        if config.TMX_OVERRIDE and config.MAP_NAME:
            foton = json.loads('[{"name":"'+config.MAP_NAME+'","tmx":"'+config.TMX_OVERRIDE+'"}]')
        else:
            foton = json.load(foton_json)

        map_data = tm.get_map_data(foton['maps'])
        if not config.PREVENT_MAP_CONSOLIDATION:
            for map_name in map_data["combined_maps"]:
                cmap_data = map_data["combined_maps"][map_name]
                bitmap,tilemap_width,success = tc.create_tilemap(cmap_data,True)
                if success:
                    for combined_map in cmap_data["maps"]:
                        map_data["maps"][combined_map]["combined_tilemap"] = {
                            "mapdict":cmap_data,
                            "bitmap":bitmap,
                            "tilemap_width":tilemap_width
                        }

        for map_name in map_data["maps"]:
            Map = MapObject()
            Map.init(map_data["maps"][map_name])
            Map.gather_map_data()
            Map.calculate_tilemap_data()
            all_maps.append(Map)

            if not config.FORCE_MAP_DATA_GENERATION and \
               os.path.exists("include/" + Map.name + ".hpp") and \
               os.path.getctime("include/" + Map.name + ".hpp") >= \
                   os.path.getctime(Map.tmx_filepath) and \
               os.path.exists("src/" + Map.name + ".cpp") and \
               os.path.getctime("src/" + Map.name + ".cpp") >= \
                   os.path.getctime(Map.tmx_filepath):
                print("Source tiled map not modified, skipping generation of new data files")
            else:
                mg.write_tilemap_header_file(Map)
                mg.write_tilemap_cpp_file(Map)

    if config.CREATE_GLOBALS_FILE:
        mg.write_tilemap_globals_file()

    print("Finished")
