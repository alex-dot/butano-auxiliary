#!/usr/bin/env python

"""tilemap_compressor.py: Generate compressed tilemap bitmaps from referenced tilemaps in 
                          tiled projects. """

import os
import sys
import json
import argparse
from numpy import subtract
from PIL import Image, ImageOps

import config
import tilemap_minimizer as tm
from mapdata_models import TilemapImageObject

def tile_compare(left, right):
    '''Does a pixel by pixel comparison of 8x8 tile. Returns True if all pixels are the same
       color, return False otherwise.'''
    for x in range(8):
        for y in range(8):
            if (subtract(left.getpixel((x,y)),right.getpixel((x,y))) != [0,0,0]).any():
                return False
    return True

def compare_tiles(tilemap_src):
    '''Creates a tiles for a tilemap which (a) defines unique tiles, (b) references to a unique
       tile if a tile is not unique, (c) flags if tile is a flipped version of the referenced tile
       and (d) the number of preceeding non unique tiles. '''

    columns = int( tilemap_src.width / 8 )
    rows = int( tilemap_src.height / 8 )

    tilemap_tiles = [ {
        'unique': True, 
        'relative': (0,0), 
        'h_flipped': False, 
        'v_flipped': False, 
        'non_unique_tile_count': 0 } for x in range(rows*columns) ]

    for y in range(rows):
        for x in range(columns):
            if not tilemap_tiles[y*columns+x]['unique']:
                continue
            region = (x*8,y*8,(x+1)*8,(y+1)*8)
            tile = tilemap_src.crop(region)
            for j in range(y,rows):
                for i in range(columns):
                    if j == y and i <= x:
                        continue
                    comp_region = (i*8,j*8,(i+1)*8,(j+1)*8)
                    comp_tile = tilemap_src.crop(comp_region)
                    if tile_compare(tile, comp_tile):
                        tilemap_tiles[j*columns+i]['unique'] = False
                        tilemap_tiles[j*columns+i]['relative'] = (x,y)
                        continue
                    comp_tile = ImageOps.flip(comp_tile)
                    if tile_compare(tile, comp_tile):
                        tilemap_tiles[j*columns+i]['unique'] = False
                        tilemap_tiles[j*columns+i]['relative'] = (x,y)
                        tilemap_tiles[j*columns+i]['v_flipped'] = True
                        continue
                    comp_tile = tilemap_src.crop(comp_region)
                    comp_tile = comp_tile.rotate(180)
                    if tile_compare(tile, comp_tile):
                        tilemap_tiles[j*columns+i]['unique'] = False
                        tilemap_tiles[j*columns+i]['relative'] = (x,y)
                        tilemap_tiles[j*columns+i]['v_flipped'] = True
                        tilemap_tiles[j*columns+i]['h_flipped'] = True
                        continue
                    comp_tile = tilemap_src.crop(comp_region)
                    comp_tile = comp_tile.rotate(180)
                    comp_tile = ImageOps.flip(comp_tile)
                    if tile_compare(tile, comp_tile):
                        tilemap_tiles[j*columns+i]['unique'] = False
                        tilemap_tiles[j*columns+i]['relative'] = (x,y)
                        tilemap_tiles[j*columns+i]['h_flipped'] = True
                        continue

    unique_tile_count = 0
    for y in range(rows):
        for x in range(columns):
            if tilemap_tiles[y*columns+x]['unique']:
                unique_tile_count += 1

    return tilemap_tiles,unique_tile_count

def create_tilemap_palette(tilemap_min,image_file_name):
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
    #if palette_list[0][0] == 0 and palette_list[0][1] == 0 and palette_list[0][2] == 0:
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

    tilemap_palette.save("graphics/"+image_file_name+"_palette.bmp", "BMP")

    with open("graphics/"+image_file_name+"_palette.json","w",encoding='UTF-8')\
      as json_file:
        json_file.write("{\n")
        json_file.write("    \"type\": \"bg_palette\",\n")
        if len(palette_list) <= 16:
            json_file.write("    \"bpp_mode\": \"bpp_4\",\n")
        else:
            json_file.write("    \"bpp_mode\": \"bpp_8\",\n")
        json_file.write("    \"colors_count\": \"" + str(len(palette_list)) + "\"\n")
        json_file.write("}")

    return palette_list, palette_list_flat

def get_tilemap_size(tile_count):
    '''We are supporting three tilemap image sizes, depending on tile count. Values in pixels.'''
    if tile_count <= 256:
        tilemap_min_width, tilemap_min_height = 128,128
    elif tile_count <= 512:
        tilemap_min_height = 128
        tilemap_min_width = 128 + int((tile_count-256)/16+1)*8
    elif tile_count <= 960:
        tilemap_min_height = 128 + int((tile_count-512)/32+1)*8
        tilemap_min_width = 256
    return tilemap_min_width,tilemap_min_height

def create_rgb_tilemap_image(tilemap, tilemap_tiles):
    '''Creates the compressed tilemap as an RGB image in memory.'''
    non_unique_tiles = 0
    tilemap.min_rgb = Image.new(
        'RGB',
        (tilemap.min_width, tilemap.min_height),
        tilemap.original.getpixel((0,0))
    )
    i,j = 0,0
    for y in range(tilemap.rows):
        for x in range(tilemap.columns):
            if tilemap_tiles[y*tilemap.columns+x]['unique']:
                region = (x*8,y*8,(x+1)*8,(y+1)*8)
                tile = tilemap.original.crop(region)
                region = (j*8,i*8,(j+1)*8,(i+1)*8)
                tilemap.min_rgb.paste(tile, region)
                j += 1
                if j >= tilemap.min_width/8:
                    i += 1
                    j = 0
            else:
                non_unique_tiles += 1
            tilemap_tiles[y*tilemap.columns+x]["non_unique_tile_count"] = non_unique_tiles
    return tilemap,tilemap_tiles

def create_paletted_tilemap_image(tilemap,palette_list,palette_list_flat):
    '''Creates final compressed tilemap image using generated palette list.'''
    tilemap_min_p = Image.new(
        'P',
        (tilemap.min_width, tilemap.min_height),
        (255,0,255)
    )
    tilemap_min_p.putpalette(palette_list_flat)
    for y in range(tilemap.min_height):
        for x in range(tilemap.min_width):
            rgb = tilemap.min_rgb.getpixel((x,y))
            try:
                pindex = palette_list.index(rgb)
            except ValueError:
                if rgb == (0,0,0):
                    pindex = palette_list.index((255,0,255))
            tilemap_min_p.putpixel((x,y),pindex)

    tilemap_min_p.save("graphics/" + tilemap.name + ".bmp","BMP")

def create_butano_json_import_file(tilemap_name, palette_list):
    '''Creates json file for butano import. Automatically sets appropriate color depth.'''
    with open("graphics/" + tilemap_name + ".json","w",encoding='UTF-8')\
      as json_file:
        json_file.write("{\n")
        json_file.write("    \"type\": \"regular_bg_tiles\",\n")
        if len(palette_list) <= 16:
            json_file.write("    \"bpp_mode\": \"bpp_4\"\n")
        else:
            json_file.write("    \"bpp_mode\": \"bpp_8\"\n")
        json_file.write("}\n")

def create_compressed_tileset(mapdict):
    '''Creating compressed tilemap from a regular tilemap file by searching for duplicated
       tiles. Supports horizontal and vertical flipping.'''

    if config.PREVENT_TILEMAP_MINIMIZATION and len(mapdict['images']) == 1:
        tilemap_src = Image.open(
            "graphics/ressources/" + next(iter(mapdict['images'].values()))['image_src']
        ).convert('RGB')
    else:
        tilemap_src = mapdict['tilemap']

    tilemap_tiles,unique_tile_count = compare_tiles(tilemap_src)

    if unique_tile_count <= 960:
        print("Found "+str(unique_tile_count)+" unique tiles, generating compressed tilemap...")
    else:
        raise OverflowError("Too many unique tiles found: "+str(unique_tile_count))

    tilemap_min_width,tilemap_min_height = get_tilemap_size(unique_tile_count)

    tilemap = TilemapImageObject(
        mapdict['map_name'],
        int( tilemap_src.height / 8 ),
        int( tilemap_src.width / 8 ),
        tilemap_src,
        tilemap_min_width,
        tilemap_min_height
    )

    tilemap,tilemap_tiles = create_rgb_tilemap_image(tilemap,tilemap_tiles)

    print("Minimized tilemap created, extracting palette...")
    palette_list, palette_list_flat = create_tilemap_palette(tilemap.min_rgb,mapdict['map_name'])

    print("Palette extracted, applying to compressed tileset...")
    create_paletted_tilemap_image(tilemap,palette_list,palette_list_flat)
    create_butano_json_import_file(tilemap.name,palette_list)

    print("Palette applied, storing meta information in ressource folder...")
    with open("graphics/ressources/" + mapdict['map_name'] + ".json","w",encoding='UTF-8')\
      as json_output:
        output = {
            'columns':tilemap.columns,
            'minimized':config.PREVENT_TILEMAP_MINIMIZATION,
            'tilemap':tilemap_tiles
        }
        json.dump(output, json_output)

    print("Tileset created")
    return tilemap_tiles, tilemap.columns

def get_tiles(map_name):
    '''Load tilemap metadata file and return tiles used as well as the number of tiles
       per line in source image and whether the information in the tilemap metadata file is 
       consistent with the current value of the PREVENT_TILEMAP_MINIMIZATION flag.'''
    with open("graphics/ressources/" + map_name + ".json",encoding='UTF-8')\
      as cached_tilemap_json_file:
        cached_tilemap_json = json.load(cached_tilemap_json_file)
    tiles = cached_tilemap_json["tilemap"]
    tilemap_width = int(cached_tilemap_json["columns"])
    return tiles,tilemap_width,bool(
        bool(config.PREVENT_TILEMAP_MINIMIZATION and not cached_tilemap_json["minimized"]) or
        bool(not config.PREVENT_TILEMAP_MINIMIZATION and cached_tilemap_json["minimized"])
    )

def create_tilemap(mapdict, combined_map=False):
    '''Parses butano tilemap JSON file in graphics/ to extract tiled map location, then parses
       tiled map file. Calls subsequent functions to compress all referenced tilemaps and create
       butano header file containing map data. Expects "tmx" value in JSON file to point to tiled 
       map file.'''
    print("creating compressed tileset: " + mapdict['map_name'])
    tiles, tilemap_width = "", ""
    latest_image_change_date = -1
    for img in mapdict['images']:
        if os.path.getctime(
          "graphics/ressources/" + mapdict["images"][img]['image_src']
        ) > latest_image_change_date:
            latest_image_change_date = os.path.getctime(
                "graphics/ressources/" + mapdict["images"][img]['image_src']
            )

    generate_image = True
    if not config.FORCE_IMAGE_GENERATION and \
       os.path.exists("graphics/ressources/" + mapdict['map_name'] + ".json") and \
       os.path.getctime("graphics/" + mapdict['map_name'] + ".bmp") >= latest_image_change_date:
        tiles,tilemap_width,generate_image = get_tiles(mapdict['map_name'])

    # Only generate the compressed tileset if
    # a) image generation is NOT forced, or
    # b) the source tilemap image has changed since last image generation, or
    # c1) a tilemap metadata file containing tiles used information exists, and
    # c2) the information in the tilemap metadata file is consistent with the
    #     current value of the PREVENT_TILEMAP_MINIMIZATION flag
    if generate_image:
        try:
            tiles,tilemap_width = create_compressed_tileset(mapdict)
        except OverflowError as e:
            if not combined_map:
                raise e
            print("Too many unique tiles found but ignoring this since "+\
                  mapdict["map_name"]+" is a consolidated tilemap")
            return None,None,False
    else:
        print("Source image not modified, skipping generation of new compressed tileset")


    return tiles,tilemap_width,True

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate compressed tilemap bitmaps from referenced tilemaps in tiled projects.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
    argparser.add_argument('--force-image-gen',dest='force_img',action='store_true',
                           help='Force tilemap image generation')
    argparser.add_argument('-s','--save-temp-files',dest='save_temp_imgs',action='store_true',
                           help='Save temporary files (like *_minimized.bmp and *_combined.bmp '+\
                                'and some json files)')
    argparser.add_argument('--map-file',dest='tmx_override',
                           help='Specifiy tiled TMX map, ignoring foton.json; requires --map-name')
    argparser.add_argument('--map-name',dest='map_name',
                           help='Specifiy map name, ignoring foton.json; requires --map-file')
    argparser.add_argument('--no-minimization',dest='prevent_minimization',action='store_true',
                           help='Do not minimize tilemap before compression')
    argparser.add_argument('--no-map-consolidation',dest='prevent_consolidation',
                           action='store_true',
                           help='Prevent consolidation of maps so each map will have their '+\
                                'own generated tilemap')
    args = argparser.parse_args()

    if args.force:
        config.FORCE_IMAGE_GENERATION = True
    if args.force_img:
        config.FORCE_IMAGE_GENERATION = True
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

    with open("graphics/ressources/foton.json",encoding='UTF-8') as foton_json:
        if config.TMX_OVERRIDE and config.MAP_NAME:
            foton = json.loads('[{"name":"'+config.MAP_NAME+'","tmx":"'+config.TMX_OVERRIDE+'"}]')
        else:
            foton = json.load(foton_json)

        map_data = tm.get_map_data(foton['maps'])
        if not config.PREVENT_MAP_CONSOLIDATION:
            for map_name in map_data["combined_maps"]:
                tiles,tilemap_width,success = create_tilemap(
                    map_data["combined_maps"][map_name], True
                )
                if success:
                    for combined_map in map_data["combined_maps"][map_name]["maps"]:
                        map_data["maps"][combined_map]["combined_tilemap"] = {
                            "mapdict":map_data["combined_maps"][map_name],
                            "bitmap":tiles
                        }

        for map_name in map_data["maps"]:
            if config.PREVENT_MAP_CONSOLIDATION or \
               not map_data["maps"][map_name]["combined_tilemap"]:
                create_tilemap(map_data["maps"][map_name])
            else:
                print("Skipping generation of tileset \""+map_name+"\" since it is included in: "\
                      +map_data["maps"][map_name]["combined_tilemap"]["mapdict"]["map_name"])

    print("Finished")
