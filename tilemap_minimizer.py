#!/usr/bin/env python

"""tilemap_minimizer.py: Generate minimized tilemaps and butano-compatible map headers from tiled 
                         projects. This script assumes to be run from the root folder of a butano 
                         project."""

import os
import sys
import json
import argparse
from xml.dom.minidom import parse as xmlparse
from numpy import subtract
from PIL import Image, ImageOps

H_FLIP = 1024
V_FLIP = 2048

FORCE_IMAGE_GENERATION = False
NAMESPACE = ""
PARSE_OBJECTS = False

def pixel_compare(left, right):
    '''Does a pixel by pixel comparison of 8x8 tile. Returns True if all pixels are the same
       color, return False otherwise.'''
    for x in range(8):
        for y in range(8):
            if (subtract(left.getpixel((x,y)),right.getpixel((x,y))) != [0,0,0]).any():
                return False
    return True

def compare_tiles(tilemap, columns, rows):
    '''Creates a bitmap for a tilemap which (a) defines unique tiles, (b) references to a unique
       tile if a tile is not unique, (c) flags if tile is a flipped version of the referenced tile
       and (d) the number of preceeding non unique tiles. '''
    tilemap_bitmap = [ {
        'unique': True, 
        'relative': (0,0), 
        'h_flipped': False, 
        'v_flipped': False, 
        'non_unique_tile_count': 0 } for x in range(rows*columns) ]

    for y in range(rows):
        for x in range(columns):
            if not tilemap_bitmap[y*columns+x]['unique']:
                continue
            region = (x*8,y*8,(x+1)*8,(y+1)*8)
            tile = tilemap.crop(region)
            for j in range(y,rows):
                for i in range(columns):
                    if j == y and i <= x:
                        continue
                    comp_region = (i*8,j*8,(i+1)*8,(j+1)*8)
                    comp_tile = tilemap.crop(comp_region)
                    if pixel_compare(tile, comp_tile):
                        tilemap_bitmap[j*columns+i]['unique'] = False
                        tilemap_bitmap[j*columns+i]['relative'] = (x,y)
                        continue
                    comp_tile = ImageOps.flip(comp_tile)
                    if pixel_compare(tile, comp_tile):
                        tilemap_bitmap[j*columns+i]['unique'] = False
                        tilemap_bitmap[j*columns+i]['relative'] = (x,y)
                        tilemap_bitmap[j*columns+i]['v_flipped'] = True
                        continue
                    comp_tile = tilemap.crop(comp_region)
                    comp_tile = comp_tile.rotate(180)
                    if pixel_compare(tile, comp_tile):
                        tilemap_bitmap[j*columns+i]['unique'] = False
                        tilemap_bitmap[j*columns+i]['relative'] = (x,y)
                        tilemap_bitmap[j*columns+i]['v_flipped'] = True
                        tilemap_bitmap[j*columns+i]['h_flipped'] = True
                        continue
                    comp_tile = tilemap.crop(comp_region)
                    comp_tile = comp_tile.rotate(180)
                    comp_tile = ImageOps.flip(comp_tile)
                    if pixel_compare(tile, comp_tile):
                        tilemap_bitmap[j*columns+i]['unique'] = False
                        tilemap_bitmap[j*columns+i]['relative'] = (x,y)
                        tilemap_bitmap[j*columns+i]['h_flipped'] = True
                        continue

    unique_tile_count = 0
    for y in range(rows):
        for x in range(columns):
            if tilemap_bitmap[y*columns+x]['unique']:
                unique_tile_count += 1

    return tilemap_bitmap,unique_tile_count

def create_tilemap_palette(tilemap_min,image_src):
    '''Creating bmp palette from a tilemap. Appends butano JSON file of palette file with
       correct number of found colors.'''
    tilemap_min_width = tilemap_min.width
    tilemap_min_height = tilemap_min.height

    palette_list = []
    for y in range(tilemap_min_height):
        for x in range(tilemap_min_width):
            rgb = tilemap_min.getpixel((x,y))
            if rgb not in palette_list:
                palette_list.append(rgb)

    palette_width = 8
    palette_height = 8
    if len(palette_list) <= 64:
        palette_width = 8
        palette_height = 8
    elif len(palette_list) <= 128:
        palette_width = 16
        palette_height = 8
    elif len(palette_list) <= 256:
        palette_width = 16
        palette_height = 16
    else:
        print("Too many unique colors: "+str(len(palette_list)))
        sys.exit()

    # If the transparent pixel (0,0) is black (e.g. the loaded image was a PNG with alpha=0),
    # set it as a pink pixel instead
    if palette_list[0][0] == 0 and palette_list[0][1] == 0 and palette_list[0][2] == 0:
        palette_list[0] = (255,0,255)

    palette_list_flat = []
    for rgb in palette_list:
        palette_list_flat.append(rgb[0])
        palette_list_flat.append(rgb[1])
        palette_list_flat.append(rgb[2])
    for i in range(len(palette_list),256):
        palette_list_flat.append(0)
        palette_list_flat.append(0)
        palette_list_flat.append(0)

    tilemap_palette = Image.new('P', (palette_width,palette_height), tilemap_min.getpixel((0,0)))
    tilemap_palette.putpalette(palette_list_flat)
    i,j = 0,0
    for rgb in palette_list:
        tilemap_palette.putpixel((j,i),i*palette_width+j)
        j += 1
        if j >= palette_width:
            i += 1
            j = 0

    tilemap_palette.save("graphics/"+image_src.split(".")[0]+"_palette_1.bmp", "BMP")

    pinfo = None
    with open("graphics/"+image_src.split(".")[0]+"_palette_1.json","r",encoding='UTF-8')\
      as json_file:
        pinfo = json.load(json_file)
    with open("graphics/"+image_src.split(".")[0]+"_palette_1.json","w",encoding='UTF-8')\
      as json_file:
        pinfo["colors_count"] = str(len(palette_list))
        json.dump(pinfo,json_file,indent="  ")

    return palette_list, palette_list_flat

def create_compressed_tileset(image_src):
    '''Creating minimized tilemap from a regular tilemap file by searching for duplicated
       tiles. Supports horizontal and vertical flipping.'''
    tilemap_src = Image.open("graphics/ressources/" + image_src).convert('RGB')
    columns = int( tilemap_src.width / 8 )
    rows = int( tilemap_src.height / 8 )

    tilemap_bitmap,unique_tile_count = compare_tiles(tilemap_src, columns, rows)

    if unique_tile_count <= 960:
        print("Found "+str(unique_tile_count)+" unique tiles, generating minimized tilemap...")
    else:
        print("Too many unique tiles found: "+str(unique_tile_count))
        sys.exit()

    if unique_tile_count <= 256:
        tilemap_min_width, tilemap_min_height = 128,128
    elif unique_tile_count <= 512:
        tilemap_min_height = 128
        tilemap_min_width = 128 + int((unique_tile_count-256)/16+1)*8
    elif unique_tile_count <= 960:
        tilemap_min_height = 128 + int((unique_tile_count-512)/32+1)*8
        tilemap_min_width = 256

    non_unique_tiles = 0
    tilemap_min_rgb = Image.new(
        'RGB',
        (tilemap_min_width, tilemap_min_height),
        tilemap_src.getpixel((0,0))
    )
    i,j = 0,0
    for y in range(rows):
        for x in range(columns):
            if tilemap_bitmap[y*columns+x]['unique']:
                region = (x*8,y*8,(x+1)*8,(y+1)*8)
                tile = tilemap_src.crop(region)
                region = (j*8,i*8,(j+1)*8,(i+1)*8)
                tilemap_min_rgb.paste(tile, region)
                j += 1
                if j >= tilemap_min_width/8:
                    i += 1
                    j = 0
            else:
                non_unique_tiles += 1
            tilemap_bitmap[y*columns+x]["non_unique_tile_count"] = non_unique_tiles

    print("Minimized tilemap created, extracting palette...")
    palette_list, palette_list_flat = create_tilemap_palette(tilemap_min_rgb,image_src)

    print("Palette extracted, applying to minimized tileset...")
    tilemap_min_p = Image.new(
        'P',
        (tilemap_min_width, tilemap_min_height),
        tilemap_src.getpixel((0,0))
    )
    tilemap_min_p.putpalette(palette_list_flat)
    for y in range(tilemap_min_height):
        for x in range(tilemap_min_width):
            rgb = tilemap_min_rgb.getpixel((x,y))
            try:
                pindex = palette_list.index(rgb)
            except ValueError:
                if rgb == (0,0,0):
                    pindex = palette_list.index((255,0,255))
            tilemap_min_p.putpixel((x,y),pindex)

    tilemap_min_p.save("graphics/" + image_src.split(".")[0] + ".bmp","BMP")

    print("Palette applied, storing meta information in ressource folder...")
    with open("graphics/ressources/" + image_src.split(".")[0] + ".json","w",encoding='UTF-8')\
      as json_output:
        output = {'columns':columns,'tilemap':tilemap_bitmap}
        json.dump(output, json_output)

    print("Tileset created")
    return tilemap_bitmap, columns

def write_spawnpoint_data(spawn_point, hpp):
    hpp.write("    static const spawn_point_t spawn_point_"+spawn_point.getAttribute("name")+" = {\n")
    hpp.write("        "+str(int(float(spawn_point.getAttribute("x"))))+",\n")
    hpp.write("        "+str(int(float(spawn_point.getAttribute("y"))))+",\n")

    face_direction, default_spawn_point = None, None
    for prop in spawn_point.getElementsByTagName("property"):
        if prop.getAttribute("name") == "default":
            default_spawn_point = prop.getAttribute("value")
        if prop.getAttribute("name") == "face_direction":
            face_direction = prop.getAttribute("value")

    if face_direction == "up":
        hpp.write("        CT_CHAR_FACE_UP,\n")
    elif face_direction == "down":
        hpp.write("        CT_CHAR_FACE_DOWN,\n")
    elif face_direction == "left":
        hpp.write("        CT_CHAR_FACE_LEFT,\n")
    elif face_direction == "right":
        hpp.write("        CT_CHAR_FACE_RIGHT,\n")
    else:
        raise ValueError("In spawn_point construction: Invalid face direction found: " + face_direction)

    hpp.write("        "+default_spawn_point+",\n")

    name = spawn_point.getAttribute("name")
    if len(name) > 5:
        print("Warning: Name of spawn_point ("+name+") too long, contracted to: "+name[:5])

    hpp.write("        \""+name[0:5]+"\"\n")
    hpp.write("    };\n\n")

    return name

def write_boundary_data(blocker, hpp):
    number_of_points = len(blocker.getElementsByTagName("polygon")[0].getAttribute("points").split(" "))
    origin = (blocker.getAttribute("x"),blocker.getAttribute("y"))

    hpp.write("    static const polygon_t boundaries["+str(number_of_points*2)+"] = {\n")

    for point in blocker.getElementsByTagName("polygon")[0].getAttribute("points").split(" "):
        x = int(float(point.split(",")[0]) + float(origin[0]))
        x = str(0) if x < 0 else str(x)
        y = int(float(point.split(",")[1]) + float(origin[1]))
        y = str(0) if y < 0 else str(y)
        hpp.write("        "+x+","+y+",\n")

    hpp.write("    };\n")
    hpp.write("    static const boundary_metadata_t boundary_metadata[1] {\n")
    hpp.write("        "+str(number_of_points)+"\n")
    hpp.write("    };\n\n")

def write_object_data(objects, hpp):
    spawn_point_names = []
    boundary_count = 0

    for obj in objects.getElementsByTagName("object"):
        if obj.getAttribute("type") == "spawn_point" or obj.getAttribute("class") == "spawn_point":
            print("spawn_point")
            spawn_point_names.append(write_spawnpoint_data(obj, hpp))
        if obj.getAttribute("type") == "boundary" or obj.getAttribute("class") == "boundary":
            write_boundary_data(obj, hpp)
            boundary_count += 1

    hpp.write("    static const spawn_point_t spawn_points["+str(len(spawn_point_names))+"] = {\n")
    for name in spawn_point_names:
        hpp.write("        spawn_point_"+name+"\n")
    hpp.write("    };\n\n")
    hpp.write("    static const metadata_t metadata = {\n")
    hpp.write("        uint8_t("+str(len(spawn_point_names))+"),\n")             # spawn_point count
    hpp.write("        uint8_t("+str(boundary_count)+")\n")                      # boundary count
    hpp.write("    };\n\n")

def create_tilemap_header_file(bitmap, layers, objects, width, height, bitmap_width, image_src):
    '''Creates a butano header file defining GBA compatible map data referencing the tilemap.'''
    with open("include/" + image_src.split(".")[0] + ".hpp","w",encoding='UTF-8') as hpp:
        name_upper = image_src.split(".")[0].upper()
        name_lower = image_src.split(".")[0].lower()
        hpp.write("#ifndef " + NAMESPACE.upper() + "_" + name_upper + "_HPP\n")
        hpp.write("#define " + NAMESPACE.upper() + "_" + name_upper + "_HPP\n\n")
        hpp.write("#include \"globals.hpp\"\n")
        hpp.write("namespace " + NAMESPACE.lower() + "::tilemaps::"+name_lower+" {\n")

        if PARSE_OBJECTS and objects:
            write_object_data(objects, hpp)

        hpp.write("    static const tm_t<"+str(width)+","+str(height)+"> tilemap = {\n")

        for layer in layers:
            layer_name = layer.getAttribute("name")
            tilemap = parse_csv_tmx_map(layer.getElementsByTagName("data")[0].firstChild.nodeValue)
            hpp.write("        // "+layer_name+" layer\n")

            tilelist = "        "

            # since the GBA puts part of the map into different screenblocks depending
            # on the maps dimensions, we use this conditional to alter the map arithmetic
            screenblock_flip = bool(width == 64 and height in (32,64))
            screenblock_2nd_half = False
            i,k = 0,0

            while i < width*height:
                base_id = int((i-int(i/width)*width)/2)+(int(i/(width*2))*int(width/2))
                x_offset = i % 2
                y_offset = int(i/width) % 2

                tile_id = tilemap[base_id]-1 if tilemap[base_id] != 0 else 0
                real_id = tile_id%bitmap_width*2 + int(tile_id/bitmap_width)*bitmap_width*2*2 + \
                         y_offset*bitmap_width*2 + x_offset
                flip_offset = 0
                if bitmap[real_id]["h_flipped"]:
                    flip_offset += H_FLIP
                if bitmap[real_id]["v_flipped"]:
                    flip_offset += V_FLIP
                if not bitmap[real_id]["unique"]:
                    real_id = bitmap[real_id]["relative"][1]*bitmap_width*2 + \
                             bitmap[real_id]["relative"][0]
                real_id -= bitmap[real_id]["non_unique_tile_count"]
                real_id += flip_offset
                tilelist += str(real_id) + ","

                if (i+1) % width == 0 and i > 0:
                    tilelist += "\n"
                if (i+1) % 16 == 0 and i > 0:
                    tilelist += "\n" + "        "

                if screenblock_flip and k == int(width/2)-1:
                    i += int(width/2)
                    k = -1
                if screenblock_flip and not screenblock_2nd_half and i == width*32-1:
                    i = int(width/2)-1
                    screenblock_2nd_half = True
                if screenblock_flip and screenblock_2nd_half and i == width*32+int(width/2)-1:
                    i = width*32-1
                    screenblock_2nd_half = False
                if screenblock_flip and not screenblock_2nd_half and i == width*64-1:
                    i = width*32+int(width/2)-1
                    screenblock_2nd_half = True

                i += 1
                k += 1


            hpp.write(tilelist[:-8])

        hpp.write("        " + str(width) + ", // width\n")
        hpp.write("        " + str(height) + "  // height\n")
        hpp.write("\n    };\n}\n\n#endif\n")

def parse_csv_tmx_map(tmx_map):
    '''Parses tiled map file data (in CSV format).'''
    clean_map = []
    for val in tmx_map.split(","):
        if val in ('\n',''):
            continue
        clean_map.append(int(val))
    return clean_map

def create_map(tilemap_json):
    '''Parses butano tilemap JSON file in graphics/ to extract tiled map location, then parses
       tiled map file. Calls subsequent functions to minimize all referenced tilemaps and create
       butano header file containing map data. Expects "tmx" value in JSON file to point to tiled 
       map file.'''
    tilemap_xml = xmlparse("graphics/ressources/" + tilemap_json["tmx"])
    tilemap_tmx = tilemap_xml.documentElement.getElementsByTagName("tileset")[0]\
                                             .getAttribute("source")
    tilemap_tsx = xmlparse("graphics/ressources/" + tilemap_tmx)
    image_src = tilemap_tsx.documentElement.getElementsByTagName("image")[0]\
                                           .getAttribute("source")
    map_width = int(tilemap_xml.documentElement.getAttribute("width"))
    map_height = int(tilemap_xml.documentElement.getAttribute("height"))

    print("creating compressed tileset: " + image_src[:-4])
    if len(image_src.split(".")) > 2 :
        print("Error: Image files containing periods (.) in their filenames are not supported.")
        sys.exit()
    tilemap, tilemap_width = "", ""
    if not FORCE_IMAGE_GENERATION and \
       os.path.exists("graphics/ressources/" + image_src.split(".")[0] + ".json") and \
       os.path.getctime("graphics/" + image_src.split(".")[0] + ".bmp") >= \
           os.path.getctime("graphics/ressources/" + image_src):
        print("Source image not modified, skipping generation of new minified tileset")
        tilemap_json = None
        with open("graphics/ressources/" + image_src.split(".")[0] + ".json",encoding='UTF-8')\
          as tilemap_json_file:
            tilemap_json = json.load(tilemap_json_file)
        tilemap = tilemap_json["tilemap"]
        tilemap_width = int(tilemap_json["columns"])
    else:
        tilemap, tilemap_width = create_compressed_tileset(image_src)

    print("Converting map data")
    objects = None
    if PARSE_OBJECTS:
        for object_group in tilemap_xml.documentElement.getElementsByTagName("objectgroup"):
            if object_group.getAttribute("name") == "actors":
                objects = object_group
    layers = tilemap_xml.documentElement.getElementsByTagName("layer")
    create_tilemap_header_file(
        tilemap, layers, objects,
        map_width*2, map_height*2,
        int(tilemap_width*8/16),  # 16 = tilesize
        image_src
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
        hpp.write("#ifndef CT_GLOBALS_TILEMAPS_HPP\n")
        hpp.write("#define CT_GLOBALS_TILEMAPS_HPP\n\n")
        if NAMESPACE:
            hpp.write("namespace "+NAMESPACE.lower()+"::tilemaps {\n\n")
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

        if PARSE_OBJECTS:
            hpp.write("    struct spawn_point_t {\n")
            hpp.write("        uint16_t x;\n")
            hpp.write("        uint16_t y;\n")
            hpp.write("        uint8_t direction;\n")
            hpp.write("        bool    dflt;\n")
            hpp.write("        char    name[6];\n")
            hpp.write("    };\n")
            hpp.write("    struct metadata_t {\n")
            hpp.write("        uint8_t number_of_spawn_points;\n")
            hpp.write("        uint8_t number_of_boundaries;\n")
            hpp.write("    };\n\n")
            hpp.write("    struct point_t {\n")
            hpp.write("        uint16_t x;\n")
            hpp.write("        uint16_t y;\n")
            hpp.write("    };\n")
            hpp.write("    struct polygon_t {\n")
            hpp.write("        point_t point;\n")
            hpp.write("    };\n")
            hpp.write("    struct boundary_metadata_t {\n")
            hpp.write("        uint32_t number_of_points;\n")
            hpp.write("    };\n")

        hpp.write("}\n\n")
        hpp.write("#endif\n\n")

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate minimized tilemaps and butano-compatible map headers from tiled projects. 
            This script assumes to be run from the root folder of a butano project.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force image generation')
    argparser.add_argument('-n','--namespace',dest='namespace',
                           help='Set namespace for project')
    argparser.add_argument('-a','--create-actors',dest='actors',action='store_true',
                           help='Parse object layers')
    args = argparser.parse_args()

    if args.force:
        FORCE_IMAGE_GENERATION = True
    if args.namespace:
        NAMESPACE = args.namespace
    if args.actors:
        PARSE_OBJECTS = True

    for file in os.listdir("graphics"):
        if file[-5:] == ".json" and file[-15:-6] != "_palette_":
            with open("graphics/" + file,encoding='UTF-8') as json_file:
                tilemap_json = json.load(json_file)
                if "tmx" in tilemap_json:
                    create_map(tilemap_json)

    create_tilemap_globals_file()

    print("Finished")
