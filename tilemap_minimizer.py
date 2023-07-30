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

def create_minimized_tileset(image_src, image_file_name, tilesize, used_tiles):
    tilemap_src = Image.open("graphics/ressources/" + image_src).convert('RGB')
    tilemap_min = Image.new(
        'RGB',
        (tilemap_src.width, tilemap_src.height),
        tilemap_src.getpixel((0,0))
    )
    i,j = 0,0
    for tid in used_tiles:
        x = tid % int( tilemap_src.width / tilesize )
        y = int(tid / int( tilemap_src.width / tilesize ))
        region = (x*tilesize,y*tilesize,(x+1)*tilesize,(y+1)*tilesize)
        tile = tilemap_src.crop(region)
        region = (j*tilesize,i*tilesize,(j+1)*tilesize,(i+1)*tilesize)
        tilemap_min.paste(tile, region)
        j += 1
        if j >= tilemap_src.width/tilesize:
            i += 1
            j = 0
    tilemap_min.save("graphics/ressources/" + image_file_name + "_minimized.bmp","BMP")

def get_used_tiles_metadata():
    used_tiles = None
    if not os.path.exists("graphics/ressources/tile_use_map.json") or \
      os.path.getsize("graphics/ressources/tile_use_map.json") == 0:
        used_tiles = json.loads('[]')
    else:
      with open("graphics/ressources/tile_use_map.json","r",encoding='UTF-8')\
        as json_output:
            used_tiles = json.load(json_output)
    return used_tiles

def save_used_tiles_metadata(used_tiles):
    with open("graphics/ressources/tile_use_map.json","w",encoding='UTF-8')\
      as json_output:
        json.dump(used_tiles, json_output, indent=4)


def open_map(tilemap_json):
    map_name = tilemap_json["name"]
    tilemap_tmx_path = "graphics/ressources/" + tilemap_json["tmx"]
    tilemap_xml = xmlparse(tilemap_tmx_path)
    tilemap_tmx = tilemap_xml.documentElement.getElementsByTagName("tileset")[0]\
                                             .getAttribute("source")
    tilemap_tsx = xmlparse("graphics/ressources/" + tilemap_tmx)
    image_src = tilemap_tsx.documentElement.getElementsByTagName("image")[0]\
                                           .getAttribute("source")
    tilesize = int(tilemap_tsx.documentElement.getAttribute("tilewidth"))
    image_file_name = image_src.split("/")[len(image_src.split("/"))-1]
    image_file_name = image_file_name.split(".")[len(image_file_name.split("."))-2].lower()
    map_width = int(tilemap_xml.documentElement.getAttribute("width"))
    map_height = int(tilemap_xml.documentElement.getAttribute("height"))
    return tilemap_xml,tilemap_tmx_path,map_name,map_width,map_height,tilesize,image_file_name,image_src

def get_used_tiles(maps):
    print("scanning maps...")
    used_tiles = get_used_tiles_metadata()
    for tilemap in maps:
        tilemap_xml,Null,Null,Null,Null,tilesize,image_file_name,image_src = open_map(tilemap)
        used_tiles = find_used_tiles(tilemap_xml, image_file_name, image_src, tilesize, used_tiles)
    for ut in used_tiles:
        print("creating minimized tileset: " + ut["image_file_name"])
        if config.FORCE_IMAGE_GENERATION or not config.PREVENT_TILEMAP_MINIMIZATION:
            create_minimized_tileset(ut["image_src"], ut["image_file_name"], ut["tilesize"], ut["used_tiles"])
    save_used_tiles_metadata(used_tiles)
    return used_tiles

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(
        description="""
            Generate minimized tilemaps from referenced tilemaps in tiled projects.
            """)
    argparser.add_argument('-f','--force',dest='force',action='store_true',
                           help='Force all files generation')
    argparser.add_argument('--force-image-gen',dest='force_img',action='store_true',
                           help='Force tilemap image generation')
    args = argparser.parse_args()

    if args.force:
        config.FORCE_IMAGE_GENERATION = True
    if args.force_img:
        config.FORCE_IMAGE_GENERATION = True

    with open("graphics/ressources/maps.json") as maps_json:
        maps = json.load(maps_json)
        get_used_tiles(maps)

    print("Finished")
