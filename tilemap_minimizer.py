#!/usr/bin/env python

"""tilemap_minimizer.py: Generate minimized tilemaps from tilemaps referenced in tiled projects. """

import os
import sys
import json
import math
import argparse
from xml.dom.minidom import parse as xmlparse
from numpy import subtract
from PIL import Image, ImageOps

import config



# map
# -> tilemap_xml
# -> tilemap_tmx_path
# -> map_name
# -> map_width
# -> map_height
# -> image_file_name
# -> -> image_src
# -> -> tilesize
# -> -> used_tiles

# combined_tilemaps
# -> image_file_name
# -> -> image_src
# -> -> tilesize
# -> -> used_tiles
# -> -> maps

def find_used_tiles(tilemap_xml, image_file_name, image_src, tilesize, used_tiles):
    new_used_tiles_var = True
    if used_tiles:
        index = [index for (index,utm) in enumerate(used_tiles) if utm["tilemap"] == image_file_name]
        if index:
            index = index[0]
            img_used_tiles = used_tiles[index]["used_tiles"]
            new_used_tiles_var = False
    if new_used_tiles_var:
        index = 0
        img_used_tiles = []

    for layer in tilemap_xml.documentElement.getElementsByTagName("layer"):
        data = layer.getElementsByTagName("data")[0].firstChild.nodeValue
        for value in data.split(","):
            if value not in ("\n",""):
                tid = int(value)-1 if int(value) != 0 else 0
                img_used_tiles.append(tid)
    img_used_tiles = list(set(img_used_tiles))
    img_used_tiles.sort()

    if new_used_tiles_var:
        used_tiles.append({
            "tilemap":image_file_name,
            "image_file_name":image_file_name,
            "image_src":image_src,
            "tilesize":tilesize,
            "used_tiles":img_used_tiles
        })
    else:
        used_tiles[index]["used_tiles"] = img_used_tiles

    return used_tiles

def find_new_used_tiles(tilemap_xml, image_file_name, image_src, tilesize, first_gid, last_gid, used_tiles):
    img_used_tiles = []
    for layer in tilemap_xml.documentElement.getElementsByTagName("layer"):
        data = layer.getElementsByTagName("data")[0].firstChild.nodeValue
        for value in data.split(","):
            if value not in ("\n",""):
                if int(value) >= first_gid and int(value) < last_gid:
                    tid = int(value)-first_gid if int(value) != 0 else 0
                    img_used_tiles.append(tid)
    img_used_tiles = list(set(img_used_tiles))
    img_used_tiles.sort()
    return img_used_tiles

def create_minimized_tileset(mapdict):
    tile_count = 0
    for img in mapdict['images']:
        tilesize_factor = int(img['tilesize']/8)
        tile_count += len(img['used_tiles'])*tilesize_factor*tilesize_factor
    height,width = 128,128
    if tile_count >= 256:
        height = 256
    if tile_count >= 512:
        width = 256
    if tile_count >= 1024:
        height = 512
    if tile_count >= 2048:
        width = 512
    if tile_count >= 4096:
        print("Too many tiles in "+mapdict['map_name']+": "+str(tile_count))
        sys.exit()

    tilemap_min = Image.new(
        'RGB',
        (width, height),
        (255,0,255)
    )

    i,j = 0,1
    for img in mapdict['images']:
        tilemap_src = Image.open("graphics/ressources/" + img['image_src']).convert('RGB')
        for tid in img['used_tiles']:
            x = tid % int( tilemap_src.width / img['tilesize'] )
            y = int(tid / int( tilemap_src.width / img['tilesize'] ))
            region = (x*img['tilesize'],y*img['tilesize'],(x+1)*img['tilesize'],(y+1)*img['tilesize'])
            tile = tilemap_src.crop(region)
            region = (j*img['tilesize'],i*img['tilesize'],(j+1)*img['tilesize'],(i+1)*img['tilesize'])
            tilemap_min.paste(tile, region)
            j += 1
            if j >= width/img['tilesize']:
                i += 1
                j = 0

    tilemap_min.save("graphics/ressources/" + mapdict['map_name'] + "_minimized.bmp","BMP")

def get_map_data_metadata(maps=[]):
    map_data = None
    if not config.FORCE_IMAGE_GENERATION and \
      os.path.exists("graphics/ressources/tile_use_map.json") and \
      os.path.getsize("graphics/ressources/tile_use_map.json") != 0:
        with open("graphics/ressources/tile_use_map.json","r",encoding='UTF-8')\
          as json_output:
            map_data = json.load(json_output)
            if maps:
                map_names = [x['name'] for x in maps]
                map_data = [x for x in map_data if x['map_name'] in map_names]
    else:
        map_data = json.loads('[]')
    return map_data

def save_map_data_metadata(map_data):
    map_data_clean = []
    for mapdict in map_data:
        map_data_clean.append({
        'tilemap_tmx_path': mapdict['tilemap_tmx_path'],
        'map_name': mapdict['map_name'],
        'map_width': mapdict['map_width'],
        'map_height': mapdict['map_height'],
        'images': mapdict['images']
    })
    with open("graphics/ressources/tile_use_map.json","w",encoding='UTF-8')\
      as json_output:
        json.dump(map_data_clean, json_output, indent=4)


def open_map(tilemap_json, map_data = []):
    map_name = tilemap_json["name"]
    tilemap_tmx_path = "graphics/ressources/" + tilemap_json["tmx"]
    tilemap_xml = xmlparse(tilemap_tmx_path)
    map_width = int(tilemap_xml.documentElement.getAttribute("width"))
    map_height = int(tilemap_xml.documentElement.getAttribute("height"))

    mapdict = {
        'tilemap_xml': tilemap_xml,
        'tilemap_tmx_path': tilemap_tmx_path,
        'map_name': map_name,
        'map_width': map_width,
        'map_height': map_height,
        'images': []
    }
    map_images = []
    map_index = -1
    if map_data:
        map_index = [map_index for (map_index,tmp) in enumerate(map_data) if tmp["map_name"] == map_name]
        if map_index:
            map_index = map_index[0]
            map_images = map_data[map_index]['images']
        else:
            map_index = -1

    tsx_list = []
    for tsx in tilemap_xml.documentElement.getElementsByTagName("tileset"):
        if len(tsx_list) > 0:
            tsx_list[len(tsx_list)-1]["last_gid"] = int(tsx.getAttribute("firstgid")) - 1
        tsx_list.append({
            "path": tsx.getAttribute("source"),
            "first_gid": int(tsx.getAttribute("firstgid")),
            "last_gid": 99999999999
        })

    for tsx in tsx_list:
        tilemap_tsx = xmlparse("graphics/ressources/" + tsx['path'])
        image_src = tilemap_tsx.documentElement.getElementsByTagName("image")[0]\
                                               .getAttribute("source")
        tilesize = int(tilemap_tsx.documentElement.getAttribute("tilewidth"))
        image_file_name = image_src.split("/")[len(image_src.split("/"))-1]
        image_file_name = image_file_name.split(".")[len(image_file_name.split("."))-2].lower()

        imgdict = {}
        if map_images:
            index = [index for (index,tmp) in enumerate(map_images) if tmp["image_file_name"] == image_file_name][0]
            imgdict = {
                'image_file_name': image_file_name,
                'image_src': image_src,
                'tilesize': tilesize,
                'first_gid': tsx["first_gid"],
                'last_gid': tsx["last_gid"],
                'used_tiles': find_new_used_tiles(tilemap_xml, image_file_name, image_src, tilesize, tsx["first_gid"], tsx["last_gid"], map_images[index])
            }
        else:
            imgdict = {
                'image_file_name': image_file_name,
                'image_src': image_src,
                'tilesize': tilesize,
                'first_gid': tsx["first_gid"],
                'last_gid': tsx["last_gid"],
                'used_tiles': find_new_used_tiles(tilemap_xml, image_file_name, image_src, tilesize, tsx["first_gid"], tsx["last_gid"], [])
            }
        mapdict['images'].append(imgdict)


    if map_index >= 0:
        map_data[map_index] = mapdict
    else:
        map_data.append(mapdict)

    return map_data

def get_used_tiles(maps):
    print("scanning maps...")
    map_data = get_map_data_metadata(maps)
    for tilemap in maps:
        map_data = open_map(tilemap, map_data)
    if config.FORCE_IMAGE_GENERATION or not config.PREVENT_TILEMAP_MINIMIZATION:
        for mapdict in map_data:
            print("creating minimized tileset: " + mapdict["map_name"])
            create_minimized_tileset(mapdict)
    save_map_data_metadata(map_data)
    return map_data

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate minimized tilemaps from referenced tilemaps in tiled projects.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
    argparser.add_argument('--force-image-gen',dest='force_img',action='store_true',
                           help='Force tilemap image generation')
    argparser.add_argument('--map-file',dest='tmx_override',
                           help='Specifiy tiled TMX map, ignoring maps.json; requires --map-name')
    argparser.add_argument('--map-name',dest='map_name',
                           help='Specifiy map name, ignoring maps.json; requires --map-file')
    args = argparser.parse_args()

    if args.force:
        config.FORCE_IMAGE_GENERATION = True
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

    with open("graphics/ressources/maps.json") as maps_json:
        if config.TMX_OVERRIDE and config.MAP_NAME:
            maps = json.loads('[{"name":"'+config.MAP_NAME+'","tmx":"'+config.TMX_OVERRIDE+'"}]')
        else:
            maps = json.load(maps_json)
        get_used_tiles(maps)

    print("Finished")
