#!/usr/bin/env python

"""butano_auxiliary.py: Generate minimized tilemaps and butano-compatible map headers from tiled
                        projects. These are meant to be imported directly into library.hpp,
                        library.cpp, map.cpp and stage.cpp, respectively."""

import os
import sys
import json
import argparse

import config
import tilemap_compressor as tc
import mapdata_generator as mg
import tilemap_minimizer as tm
from mapdata_models import MapObject

def calculate_unordered_map_size(length):
    '''Returns the smallest power of two greater than length.'''
    size = 1
    while length > (1<<size):
        size += 1
    return 1<<size

def get_map_sizes(all_maps):
    '''Creates a dictionary of all maps keyed by their WIDTH:HEIGHT.'''
    map_sizes = dict()
    for Map in all_maps:
        mapid = str(Map.width)+":"+str(Map.height)
        if mapid in map_sizes:
            map_sizes[mapid]['count'] += 1
            map_sizes[mapid]['names'].append(Map.name)
        else:
            map_sizes[mapid] = {
                'x': str(Map.width),
                'y': str(Map.height),
                'count': 1,
                'names': [Map.name]
            }
    return map_sizes

def get_total_map_size(map_sizes):
    '''Simply counts the total number of maps.'''
    count = 0
    for size in map_sizes.values():
        count += size["count"]
    return count

def write_map_instantiation_file(map_sizes):
    '''This writes all templates for all map sizes into map.cpp'''
    with open("include/map_instantiations.hpp","w",encoding="UTF-8") as hpp:
        for size in map_sizes.values():
            hpp.write("template Map::Map(\n")
            hpp.write("    const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">&,\n")
            hpp.write("    const bn::regular_bg_tiles_item&,\n")
            hpp.write("    const bn::bg_palette_item&,\n")
            hpp.write("    const ct::tilemaps::polygon_t&,\n")
            hpp.write("    const ct::tilemaps::boundary_metadata_t&,\n")
            hpp.write("    const ct::tilemaps::metadata_t&,\n")
            hpp.write("    const ct::tilemaps::polygon_t&,\n")
            hpp.write("    const ct::tilemaps::boundary_metadata_t&);\n")

def write_stage_instantiation_file(map_sizes):
    '''This writes all map creations with all map sizes into stage.cpp'''
    with open("include/stage_instantiations.hpp","w",encoding="UTF-8") as hpp:
        for size in map_sizes.values():
            hpp.write("if( map_size.width() == "+size['x']+" && map_size.height() == "+size['y']+" ) {\n")
            hpp.write("  _map = new ct::Map(\n")
            hpp.write("    lib->get_tilemap<"+size['x']+","+size['y']+">(_map_name),\n")
            hpp.write("    lib->get_tilemap_graphic(_map_name),\n")
            hpp.write("    lib->get_tilemap_palette(_map_name),\n")
            hpp.write("    lib->get_tilemap_boundaries(_map_name),\n")
            hpp.write("    lib->get_tilemap_boundary_metadata(_map_name),\n")
            hpp.write("    lib->get_tilemap_metadata(_map_name),\n")
            hpp.write("    lib->get_tilemap_gateways(_map_name),\n")
            hpp.write("    lib->get_tilemap_gateway_metadata(_map_name)\n")
            hpp.write("  );\n")
            hpp.write("} else ")
        hpp.write("{\n")
        hpp.write("  BN_ASSERT(false,\"map size was undefined in set_new_map: \",map_size.width(),\"x\",map_size.height());\n")
        hpp.write("}")

def write_library_mapinit_instantiation_file(map_sizes):
    '''This writes all member initialisations into the constructor of Library into library.hpp'''
    with open("include/library_mapinit_instantiations.hpp","w",encoding="UTF-8") as hpp:
        for size in map_sizes.values():
            hpp.write("    _tilemaps_"+size['x']+"_"+size['y']+"(init_tilemaps<"+size['x']+","+size['y']+","+str(size['count'])+">()),\n")

def write_library_pubfunc_instantiation_file(map_sizes):
    '''This writes the public function declarations into library.hpp'''
    with open("include/library_pubfunc_instantiations.hpp","w",encoding="UTF-8") as hpp:
        for size in map_sizes.values():
            hpp.write("const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">& get_tilemap_"+size['x']+"_"+size['y']+"(const bn::string<8>&) const;\n")

def write_library_tilemap_instantiation_file(map_sizes):
    '''This writes all template declarations for the different map sizes.'''
    with open("include/library_tilemap_instantiations.hpp","w",encoding="UTF-8") as hpp:
        for size in map_sizes.values():
            hpp.write("template<>\n")
            hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">*, "+str(size['count'])+">\n")
            hpp.write("        init_tilemaps<"+size['x']+","+size['y']+","+str(size['count'])+">();\n")
            hpp.write("template<> const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">& get_tilemap<"+size['x']+","+size['y']+">(const bn::string<8>&, const Library&);\n")

def write_library_member_instantiation_file(map_sizes,sprites):
    '''This writes all member variable and function declarations into library.hpp with the
       correct sizes for the unordered_maps.'''
    map_size = str(calculate_unordered_map_size(get_total_map_size(map_sizes)))
    sprite_size = str(calculate_unordered_map_size(len(sprites)))

    with open("include/library_member_instantiations.hpp","w",encoding="UTF-8") as hpp:
        hpp.write("    const bn::unordered_map<bn::string<8>, bn::size, "+map_size+"> init_tilemaps_index();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const bn::regular_bg_tiles_item*, "+map_size+"> init_tilemap_graphics();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const bn::bg_palette_item*, "+map_size+"> init_tilemap_palettes();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::spawn_point_t*, "+map_size+"> init_tilemaps_spawnpoints();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> init_tilemaps_boundaries();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> init_tilemaps_boundary_metadata();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::metadata_t*, "+map_size+"> init_tilemaps_metadata();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> init_tilemaps_gateways();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> init_tilemaps_gateway_metadata();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::actors::metadata_t*, "+map_size+"> init_tilemaps_actors_metadata();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::actors::character_t*, "+map_size+"> init_tilemaps_characters();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::actors::container_t*, "+map_size+"> init_tilemaps_containers();\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const bn::sprite_item*, "+sprite_size+"> init_sprites();\n\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, bn::size, "+map_size+"> _tilemaps_index;\n\n")

        for size in map_sizes.values():
            hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">*, "+str(size['count'])+"> _tilemaps_"+size['x']+"_"+size['y']+";\n")
        hpp.write("\n")

        hpp.write("    const bn::unordered_map<bn::string<8>, const bn::regular_bg_tiles_item*, "+map_size+"> _tilemap_graphics;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const bn::bg_palette_item*, "+map_size+"> _tilemap_palettes;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::spawn_point_t*, "+map_size+"> _tilemap_spawnpoints;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> _tilemap_boundaries;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> _tilemap_boundary_metadata;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::metadata_t*, "+map_size+"> _tilemap_metadata;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> _tilemap_gateways;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> _tilemap_gateway_metadata;\n\n")

        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::actors::metadata_t*, "+map_size+"> _tilemap_actors_metadata;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::actors::character_t*, "+map_size+"> _tilemap_characters;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const ct::actors::container_t*, "+map_size+"> _tilemap_containers;\n")
        hpp.write("    const bn::unordered_map<bn::string<8>, const bn::sprite_item*, "+sprite_size+"> _sprites;\n")

def write_library_template_instantiation_file(map_sizes,sprites):
    '''This writes all template and map fill functions into the library.cpp file.'''
    map_size = str(calculate_unordered_map_size(get_total_map_size(map_sizes)))
    sprite_size = str(calculate_unordered_map_size(len(sprites)))

    with open("include/library_template_instantiations.hpp","w",encoding="UTF-8") as hpp:
        for size in map_sizes.values():
            hpp.write("const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">& Library::get_tilemap_"+size['x']+"_"+size['y']+"(const bn::string<8>(&key)) const {\n")
            hpp.write("    return *(_tilemaps_"+size['x']+"_"+size['y']+".at(key));\n")
            hpp.write("}\n")
        hpp.write("\n")

        hpp.write("const bn::unordered_map<bn::string<8>, bn::size, "+map_size+"> Library::init_tilemaps_index() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, bn::size, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, bn::size>(\""+map_name[0:8]+"\",bn::size("+size['x']+","+size['y']+")));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const bn::regular_bg_tiles_item*, "+map_size+"> Library::init_tilemap_graphics() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const bn::regular_bg_tiles_item*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const bn::regular_bg_tiles_item*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::bg_tiles));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const bn::bg_palette_item*, "+map_size+"> Library::init_tilemap_palettes() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const bn::bg_palette_item*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const bn::bg_palette_item*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::bg_palette));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::tilemaps::spawn_point_t*, "+map_size+"> Library::init_tilemaps_spawnpoints() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::spawn_point_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::spawn_point_t*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::spawn_points));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> Library::init_tilemaps_boundaries() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::polygon_t*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::boundaries));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> Library::init_tilemaps_boundary_metadata() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::boundary_metadata_t*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::boundary_metadata));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::tilemaps::metadata_t*, "+map_size+"> Library::init_tilemaps_metadata() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::metadata_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::metadata_t*>(\""+map_name[0:8]+"\",&ct::tilemaps::"+map_name+"::metadata));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> Library::init_tilemaps_gateways() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::polygon_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::polygon_t*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::gateways));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> Library::init_tilemaps_gateway_metadata() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::boundary_metadata_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::boundary_metadata_t*>(\""+map_name[0:8]+"\",ct::tilemaps::"+map_name+"::gateway_metadata));\n")
        hpp.write("    return map;\n}\n\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::actors::metadata_t*, "+map_size+"> Library::init_tilemaps_actors_metadata() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::actors::metadata_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::actors::metadata_t*>(\""+map_name[0:8]+"\",&ct::actors::"+map_name+"::metadata));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::actors::character_t*, "+map_size+"> Library::init_tilemaps_characters() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::actors::character_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::actors::character_t*>(\""+map_name[0:8]+"\",ct::actors::"+map_name+"::characters));\n")
        hpp.write("    return map;\n}\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const ct::actors::container_t*, "+map_size+"> Library::init_tilemaps_containers() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const ct::actors::container_t*, "+map_size+"> map;\n")
        for size in map_sizes.values():
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::actors::container_t*>(\""+map_name[0:8]+"\",ct::actors::"+map_name+"::containers));\n")
        hpp.write("    return map;\n}\n\n")

        hpp.write("const bn::unordered_map<bn::string<8>, const bn::sprite_item*, "+sprite_size+"> Library::init_sprites() {\n")
        hpp.write("    bn::unordered_map<bn::string<8>, const bn::sprite_item*, "+sprite_size+"> map;\n")
        for char_name in [x['name'] for x in sprites]:
            hpp.write("    map.insert(bn::pair<bn::string<8>, const bn::sprite_item*>(\""+char_name[0:8]+"\",&bn::sprite_items::"+char_name+"));\n")
        hpp.write("    return map;\n}\n\n")

        hpp.write("namespace tilemaps {\n")
        for size in map_sizes.values():
            hpp.write("template<> const bn::unordered_map<bn::string<8>, const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">*, "+str(size['count'])+"> init_tilemaps<"+size['x']+","+size['y']+","+str(size['count'])+">() {\n")
            hpp.write("    bn::unordered_map<bn::string<8>, const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">*, "+str(size['count'])+"> map;\n")
            for map_name in size["names"]:
                hpp.write("    map.insert(bn::pair<bn::string<8>, const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">*>(\""+map_name[0:8]+"\",&ct::tilemaps::"+map_name+"::tilemap));\n")
            hpp.write("    return map;\n")
            hpp.write("}\n\n")

        for size in map_sizes.values():
            hpp.write("template<> const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">& get_tilemap<"+size['x']+","+size['y']+">(const bn::string<8>(&key), const Library(&lib)) {\n")
            hpp.write("    return lib.get_tilemap_"+size['x']+"_"+size['y']+"(key);\n")
            hpp.write("}\n")
        hpp.write("}\n\n")

        for size in map_sizes.values():
            hpp.write("template const ct::tilemaps::tm_t<"+size['x']+","+size['y']+">& Library::get_tilemap<"+size['x']+","+size['y']+">(const bn::string<8>&) const;\n")
        hpp.write("}\n\n")


def write_instantiation_files(all_maps,sprites):
    '''Wrapper function calling all instantiation functions.'''
    map_sizes = get_map_sizes(all_maps)

    write_map_instantiation_file(map_sizes)
    write_stage_instantiation_file(map_sizes)

    write_library_mapinit_instantiation_file(map_sizes)
    write_library_pubfunc_instantiation_file(map_sizes)
    write_library_tilemap_instantiation_file(map_sizes)
    write_library_member_instantiation_file(map_sizes,sprites)
    write_library_template_instantiation_file(map_sizes,sprites)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate butano-compatible map headers from tiled projects.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
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

        all_maps = []
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
        
        write_instantiation_files(all_maps,foton['sprites'])

    if config.CREATE_GLOBALS_FILE:
        mg.write_tilemap_globals_file()

    print("Finished")
