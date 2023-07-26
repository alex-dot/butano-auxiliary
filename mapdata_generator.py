#!/usr/bin/env python

"""mapdata_generator.py: Generate butano-compatible map headers from tiled projects."""

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

def create_tilemap_header_file(spawn_point_names, boundary_data, gateway_data, width, height, image_src):
    '''Creates a butano header file defining GBA compatible map data referencing the tilemap.'''
    with open("include/" + image_src.split(".")[0] + ".hpp","w",encoding='UTF-8') as hpp:
        name_upper = image_src.split(".")[0].upper()
        name_lower = image_src.split(".")[0].lower()
        hpp.write("#ifndef " + config.NAMESPACE_UNDERSCORE.upper() + name_upper + "_HPP\n")
        hpp.write("#define " + config.NAMESPACE_UNDERSCORE.upper() + name_upper + "_HPP\n\n")
        hpp.write("#include \"globals.hpp\"\n")
        hpp.write("namespace " + config.NAMESPACE_COLON.lower() + "tilemaps::"+name_lower+" {\n")

        if config.PARSE_ACTORS:
            for name in spawn_point_names:
                hpp.write("    extern const spawn_point_t spawn_point_"+name+";\n")
            hpp.write("    extern const spawn_point_t spawn_points["+str(len(spawn_point_names))+"];\n")
        if config.PARSE_ACTORS:
            number_of_points = [x['number_of_points'] for x in gateway_data]
            hpp.write("    extern const polygon_t gateways["+str(sum(number_of_points)*2)+"];\n")
            hpp.write("    extern const boundary_metadata_t gateway_metadata["+str(len(gateway_data))+"];\n")
        if config.PARSE_BOUNDARIES:
            number_of_points = [x['number_of_points'] for x in boundary_data]
            hpp.write("    extern const polygon_t boundaries["+str(sum(number_of_points)*2)+"];\n")
            hpp.write("    extern const boundary_metadata_t boundary_metadata["+str(len(boundary_data))+"];\n")
        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            hpp.write("    extern const metadata_t metadata;\n")

        hpp.write("    extern const tm_t<"+str(width)+","+str(height)+"> tilemap;\n")
        hpp.write("\n}\n\n")

        hpp.write("namespace " + config.NAMESPACE_COLON.lower() + "texts::"+name_lower+" {\n")
        hpp.write("    extern const text_t text;\n")
        hpp.write("\n}\n\n")

        hpp.write("namespace " + config.NAMESPACE_COLON.lower() + "actors::"+name_lower+" {\n")
        hpp.write("    extern const container_t chest01;\n")
        hpp.write("    extern const container_t* containers;\n")
        hpp.write("    alignas(int) extern const metadata_t metadata;\n")

        hpp.write("\n}\n\n#endif\n")

def parse_csv_tmx_map(tmx_map):
    '''Parses tiled map file data (in CSV format).'''
    clean_map = []
    for val in tmx_map.split(","):
        if val in ('\n',''):
            continue
        clean_map.append(int(val))
    return clean_map

def create_tilemap_data(bitmap, layers, width, height, bitmap_width, tilesize_factor, cpp):
    cpp.write("    const tm_t<"+str(width)+","+str(height)+"> tilemap = {\n")

    for layer in layers:
        layer_name = layer.getAttribute("name")
        tilemap = parse_csv_tmx_map(layer.getElementsByTagName("data")[0].firstChild.nodeValue)
        cpp.write("        // "+layer_name+" layer\n")

        tilelist = "        "

        # since the GBA/butano puts part of the map into different screenblocks depending
        # on the maps dimensions, we use this conditional to alter the map arithmetic
        screenblock_flip = bool(width == 64 and height in (32,64))
        screenblock_2nd_half = False
        i,k = 0,0

        while i < width*height:
            base_id = int((i-int(i/width)*width)/tilesize_factor)+(int(i/(width*tilesize_factor))*int(width/tilesize_factor))
            x_offset = i % tilesize_factor
            y_offset = int(i/width) % tilesize_factor

            tile_id = tilemap[base_id]-1 if tilemap[base_id] != 0 else 0
            real_id = tile_id%bitmap_width*tilesize_factor + int(tile_id/bitmap_width)*bitmap_width*tilesize_factor*tilesize_factor + \
                      y_offset*bitmap_width*tilesize_factor + x_offset
            flip_offset = 0
            if bitmap[real_id]["h_flipped"]:
                flip_offset += config.H_FLIP
            if bitmap[real_id]["v_flipped"]:
                flip_offset += config.V_FLIP
            if not bitmap[real_id]["unique"]:
                real_id = bitmap[real_id]["relative"][1]*bitmap_width*tilesize_factor + \
                         bitmap[real_id]["relative"][0]
            real_id -= bitmap[real_id]["non_unique_tile_count"]
            real_id += flip_offset
            tilelist += str(real_id) + ","

            if (i+1) % width == 0 and i > 0:
                tilelist += "\n"
            if (i+1) % 16 == 0 and i > 0:
                tilelist += "\n" + "        "

            if screenblock_flip and k == int(width/tilesize_factor)-1:
                i += int(width/tilesize_factor)
                k = -1
            if screenblock_flip and not screenblock_2nd_half and i == width*32-1:
                i = int(width/tilesize_factor)-1
                screenblock_2nd_half = True
            if screenblock_flip and screenblock_2nd_half and i == width*32+int(width/tilesize_factor)-1:
                i = width*32-1
                screenblock_2nd_half = False
            if screenblock_flip and not screenblock_2nd_half and i == width*64-1:
                i = width*32+int(width/tilesize_factor)-1
                screenblock_2nd_half = True

            i += 1
            k += 1


        cpp.write(tilelist[:-8])

    cpp.write("        " + str(width) + ", // width\n")
    cpp.write("        " + str(height) + "  // height\n")
    cpp.write("\n    };\n")

def write_boundary_data(boundary_data, typename, cpp):
    number_of_points = [x['number_of_points'] for x in boundary_data]
    cpp.write("    const polygon_t "+typename+"["+str(sum(number_of_points)*2)+"] = {\n")

    for boundary in boundary_data:
        for point in boundary['points']:
            cpp.write("        "+point['x']+","+point['y']+",\n")

    cpp.write("    };\n")

    return

def calculate_boundary_data(boundary):
    number_of_points = len(boundary.getElementsByTagName("polygon")[0].getAttribute("points").split(" "))
    origin = (boundary.getAttribute("x"),boundary.getAttribute("y"))

    min_x,max_x,min_y,max_y = math.inf,0,math.inf,0
    points = []

    for point in boundary.getElementsByTagName("polygon")[0].getAttribute("points").split(" "):
        x = int(float(point.split(",")[0]) + float(origin[0]))
        x = 0 if x < 0 else x
        y = int(float(point.split(",")[1]) + float(origin[1]))
        y = 0 if y < 0 else y

        min_x = x if x < min_x else min_x
        max_x = x if x > max_x else max_x
        min_y = y if y < min_y else min_y
        max_y = y if y > max_y else max_y

        points.append({'x':str(x),'y':str(y)})

    map_name,spawn_point_name = None,None
    for prop in boundary.getElementsByTagName("property"):
        if prop.getAttribute("name") == "destination":
            map_name = prop.getAttribute("value")
        if prop.getAttribute("name") == "spawnpoint":
            spawn_point_name = prop.getAttribute("value")

    return {
                'number_of_points':number_of_points, 
                'points':points,
                'min_x':str(min_x),
                'max_x':str(max_x),
                'min_y':str(min_y),
                'max_y':str(max_y),
                'map_name':map_name,
                'spawn_point_name':spawn_point_name
            }

def write_spawnpoint_data(spawn_point, cpp):
    name = spawn_point.getAttribute("name")
    if len(name) > 5:
        print("Warning: Name of spawn_point ("+name+") too long, contracted to: "+name[:5])

    cpp.write("    const spawn_point_t spawn_point_"+spawn_point.getAttribute("name")+" = {\n")
    cpp.write("        "+str(int(float(spawn_point.getAttribute("x"))))+",\n")
    cpp.write("        "+str(int(float(spawn_point.getAttribute("y"))))+",\n")

    face_direction, default_spawn_point = None, None
    for prop in spawn_point.getElementsByTagName("property"):
        if prop.getAttribute("name") == "default":
            default_spawn_point = prop.getAttribute("value")
        if prop.getAttribute("name") == "face_direction":
            face_direction = prop.getAttribute("value")

    if face_direction == "up":
        cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_UP,\n")
    elif face_direction == "down":
        cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_DOWN,\n")
    elif face_direction == "left":
        cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_LEFT,\n")
    elif face_direction == "right":
        cpp.write("        "+config.NAMESPACE_UNDERSCORE.upper()+"CHAR_FACE_RIGHT,\n")
    else:
        raise ValueError("In spawn_point construction: Invalid face direction found: " + name)

    cpp.write("        "+default_spawn_point+",\n")

    cpp.write("        \""+name[0:5]+"\"\n")
    cpp.write("    };\n")

    return name

def write_actor_data(obj, cpp):
    item_data = ["","potion"]
    chest_data = []
    for obj in obj.getElementsByTagName("object"):
        if obj.getAttribute("type") == "chest" or obj.getAttribute("class") == "chest":
            cpp.write("    const container_t "+obj.getAttribute("name")+" = {\n")
            for prop in obj.getElementsByTagName("property"):
                if prop.getAttribute("name") == "contains":
                    for item in prop.getAttribute("value").split(")"):
                        if item:
                            item_name = item_data[int(item.split(",")[0][1:])]
                            item_count = item.split(",")[1]
                            tlx = str(int(float(obj.getAttribute("x"))))
                            tly = str(int(float(obj.getAttribute("y")))-int(float(obj.getAttribute("height"))))
                            brx = str(int(float(obj.getAttribute("x")))+int(float(obj.getAttribute("width"))))
                            bry = str(int(float(obj.getAttribute("y"))))
                            cpp.write("        \""+item_name+"\","+item_count+",\n")
            cpp.write("        "+tlx+","+tly+",\n")
            cpp.write("        "+brx+","+bry+"\n")
            cpp.write("    };\n")
            chest_data.append({'name':obj.getAttribute("name")})

    cpp.write("\n    const container_t* containers = {\n")
    for chest in chest_data:
        cpp.write("        &"+chest['name']+"\n")
    cpp.write("    };\n")
    cpp.write("    const metadata_t metadata = {\n")
    cpp.write("        "+str(len(chest_data))+"\n")
    cpp.write("    };\n")

    return

def write_object_data(actors, boundaries, cpp):
    spawn_point_names = []
    boundary_data = []
    gateway_data = []

    for obj in actors.getElementsByTagName("object"):
        if obj.getAttribute("type") == "spawn_point" or obj.getAttribute("class") == "spawn_point":
            spawn_point_names.append(write_spawnpoint_data(obj, cpp))
        if obj.getAttribute("type") == "gateway" or obj.getAttribute("class") == "gateway":
            gateway_data.append(calculate_boundary_data(obj))

    for obj in boundaries.getElementsByTagName("object"):
        if obj.getAttribute("type") == "boundary" or obj.getAttribute("class") == "boundary":
            boundary_data.append(calculate_boundary_data(obj))

    write_boundary_data(gateway_data, "gateways", cpp)
    write_boundary_data(boundary_data, "boundaries", cpp)

    cpp.write("\n    const boundary_metadata_t boundary_metadata["+str(len(boundary_data))+"] {\n")
    for boundary in boundary_data:
        cpp.write("        "+str(boundary['number_of_points'])+",")
        cpp.write(str(boundary['min_x'])+",")
        cpp.write(str(boundary['max_x'])+",")
        cpp.write(str(boundary['min_y'])+",")
        cpp.write(str(boundary['max_y'])+",")
        cpp.write("\"\",\"\",\n")
    cpp.write("    };\n\n")

    cpp.write("    const boundary_metadata_t gateway_metadata["+str(len(gateway_data))+"] {\n")
    for gateway in gateway_data:
        cpp.write("        "+str(gateway['number_of_points'])+",")
        cpp.write(str(gateway['min_x'])+",")
        cpp.write(str(gateway['max_x'])+",")
        cpp.write(str(gateway['min_y'])+",")
        cpp.write(str(gateway['max_y'])+",")
        cpp.write("\""+gateway['map_name']+"\",")
        cpp.write("\""+gateway['spawn_point_name']+"\",\n")
    cpp.write("    };\n\n")

    cpp.write("    const spawn_point_t spawn_points["+str(len(spawn_point_names))+"] = {\n")
    for name in spawn_point_names:
        cpp.write("        spawn_point_"+name+",\n")
    cpp.write("    };\n\n")
    cpp.write("    const metadata_t metadata = {\n")
    cpp.write("        uint8_t("+str(len(spawn_point_names))+"),\n")      # spawn_point count
    cpp.write("        uint8_t("+str(len(boundary_data))+"),\n")           # boundary count
    cpp.write("        uint8_t("+str(len(gateway_data))+")\n")           # gateway count
    cpp.write("    };\n\n")

    return spawn_point_names,boundary_data,gateway_data

def create_tilemap_cpp_file(bitmap, layers, actors, boundaries, width, height, bitmap_width, tilesize, image_src):
    spawn_point_names,boundary_data,gateway_data = None,None,None
    name_upper = image_src.split(".")[0].upper()
    name_lower = image_src.split(".")[0].lower()

    with open("src/" + name_lower + ".cpp","w",encoding='UTF-8') as cpp:
        cpp.write("#include \""+name_lower+".hpp\"\n\n")

        # TODO requires proper handling
        cpp.write("namespace " + config.NAMESPACE_COLON.lower() + "texts::"+name_lower+" {\n")
        cpp.write("    const text_t text = \"Crono received 1 potion.\";\n")
        cpp.write("}\n\n")

        # TODO requires proper handling
        cpp.write("namespace " + config.NAMESPACE_COLON.lower() + "actors::"+name_lower+" {\n")
        write_actor_data(actors,cpp)
        cpp.write("}\n\n")

        cpp.write("namespace " + config.NAMESPACE_COLON.lower() + "tilemaps::"+name_lower+" {\n")

        if (config.PARSE_ACTORS and actors) or (config.PARSE_BOUNDARIES and boundaries):
            spawn_point_names,boundary_data,gateway_data = write_object_data(actors, boundaries, cpp)

        create_tilemap_data(bitmap, layers, width, height, bitmap_width, tilesize, cpp)

        cpp.write("}\n")

    return spawn_point_names,boundary_data,gateway_data

def create_data_files(bitmap, layers, actors, boundaries, width, height, bitmap_width, tilesize, image_src):
    spawn_point_names,boundary_data,gateway_data = create_tilemap_cpp_file(bitmap, layers, actors, boundaries, width, height, bitmap_width, tilesize, image_src)
    create_tilemap_header_file(spawn_point_names, boundary_data, gateway_data, width, height, image_src)

def create_map_data(tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,bitmap,tilemap_width,tilesize):
    print("Generating map "+map_name+" with dimensions: "+str(int(map_width*(tilesize/8)))+"x"+str(int(map_height*(tilesize/8))))
    if not config.FORCE_MAP_DATA_GENERATION and \
       os.path.exists("include/" + map_name + ".hpp") and \
       os.path.getctime("include/" + map_name + ".hpp") >= \
           os.path.getctime(tilemap_tmx_path) and \
       os.path.exists("src/" + map_name + ".cpp") and \
       os.path.getctime("src/" + map_name + ".cpp") >= \
           os.path.getctime(tilemap_tmx_path):
        print("Source tiled map not modified, skipping generation of new data files")
    else:
        actors,boundaries = None,None
        for object_group in tilemap_xml.documentElement.getElementsByTagName("objectgroup"):
            if config.PARSE_ACTORS and object_group.getAttribute("name") == "actors":
                actors = object_group
            if config.PARSE_BOUNDARIES and object_group.getAttribute("name") == "boundaries":
                boundaries = object_group
        layers = tilemap_xml.documentElement.getElementsByTagName("layer")
        create_data_files(
            bitmap, layers, actors, boundaries,
            int(map_width*(tilesize/8)), int(map_height*(tilesize/8)),
            int((tilemap_width*8)/tilesize),
            int(tilesize/8), 
            map_name
        )

    return

def create_tilemap_globals_file():
    '''Creates a butano header file defining map data structs to be used by tilemaps.'''

    with open("include/globals_tilemaps.hpp","w",encoding='UTF-8') as hpp:
        hpp.write("/*\n")
        hpp.write(" * This file is part of XXX\n")
        hpp.write(" *\n")
        hpp.write(" * Copyright (c) 2023 Alexander Herr thissideup@gmx.net\n")
        hpp.write(" *\n")
        hpp.write(" * Defines tilemap struct template as used in map header files. \n")
        hpp.write(" */\n\n")
        hpp.write("#ifndef "+config.NAMESPACE_UNDERSCORE.upper()+"GLOBALS_TILEMAPS_HPP\n")
        hpp.write("#define "+config.NAMESPACE_UNDERSCORE.upper()+"GLOBALS_TILEMAPS_HPP\n\n")
        if config.NAMESPACE:
            hpp.write("namespace "+config.NAMESPACE_COLON.lower()+"tilemaps {\n\n")
        else:
            hpp.write("namespace tilemaps {\n\n")

        hpp.write("    template<uint16_t width_, uint16_t height_>\n")
        hpp.write("    struct tm_t {\n")
        hpp.write("        uint16_t base[width_*height_];\n")
        hpp.write("        uint16_t props[width_*height_];\n")
        hpp.write("        uint16_t cover[width_*height_];\n")
        hpp.write("        uint16_t width = width_;\n")
        hpp.write("        uint16_t height = height_;\n")
        hpp.write("    };\n\n")

        if config.PARSE_ACTORS:
            hpp.write("    struct spawn_point_t {\n")
            hpp.write("        uint16_t x;\n")
            hpp.write("        uint16_t y;\n")
            hpp.write("        uint8_t direction;\n")
            hpp.write("        bool    dflt;\n")
            hpp.write("        char    name[6];\n")
            hpp.write("    };\n")
        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            hpp.write("    struct point_t {\n")
            hpp.write("        uint16_t x;\n")
            hpp.write("        uint16_t y;\n")
            hpp.write("    };\n")
            hpp.write("    struct polygon_t {\n")
            hpp.write("        point_t point;\n")
            hpp.write("    };\n")
            hpp.write("    struct boundary_metadata_t {\n")
            hpp.write("        uint32_t number_of_points;\n")
            hpp.write("        uint16_t min_x;\n")
            hpp.write("        uint16_t max_x;\n")
            hpp.write("        uint16_t min_y;\n")
            hpp.write("        uint16_t max_y;\n")
            hpp.write("        char map_name[9];\n")
            hpp.write("        char spawn_point_name[6];\n")
            hpp.write("    };\n")
        if config.PARSE_ACTORS or config.PARSE_BOUNDARIES:
            hpp.write("    struct metadata_t {\n")
            hpp.write("        uint8_t number_of_spawn_points;\n")
            hpp.write("        uint8_t number_of_boundaries;\n")
            hpp.write("        uint8_t number_of_gateways;\n")
            hpp.write("    };\n\n")

        hpp.write("}\n\n")
        hpp.write("#endif\n\n")

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate butano-compatible map headers from tiled projects.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
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
        config.FORCE_MAP_DATA_GENERATION = True
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
            tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,bitmap,tilemap_width,tilesize = create_map(tilemap)
            create_map_data(tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,bitmap,tilemap_width,tilesize)

    if config.CREATE_GLOBALS_FILE:
        create_tilemap_globals_file()

    print("Finished")
