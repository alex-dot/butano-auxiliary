#!/usr/bin/env python

"""tilemap_minimizer.py: Generate minimized tilemaps from tilemaps referenced in tiled projects. """

import os
import sys
import json
import hashlib
import argparse
from xml.dom.minidom import parse as xmlparse
from PIL import Image

import config

# From Stackoverflow: https://stackoverflow.com/a/1181922
def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, int):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36

def find_used_tiles(tilemap_xml, first_gid, last_gid):
    img_used_tiles = []
    for layer in tilemap_xml.documentElement.getElementsByTagName("layer"):
        data = layer.getElementsByTagName("data")[0].firstChild.nodeValue
        for value in data.split(","):
            if value not in ("\n",""):
                if int(value) >= first_gid and int(value) < last_gid:
                    tid = int(value)-first_gid if int(value) != 0 else 0
                    img_used_tiles.append(tid)
    img_used_tiles.append(0)
    img_used_tiles = list(set(img_used_tiles))
    img_used_tiles.sort()
    return img_used_tiles

def create_tileset(mapdict):
    tile_count = 0
    for img in mapdict['images']:
        tilesize_factor = int(mapdict['images'][img]['tilesize']/8)
        if config.PREVENT_TILEMAP_MINIMIZATION:
            tilemap = Image.open("graphics/ressources/" + mapdict['images'][img]['image_src'])
            tile_count += int(tilemap.height/8)*int(tilemap.width/8)
        else:
            tile_count += len(mapdict['images'][img]['used_tiles'])*tilesize_factor*tilesize_factor
    height,width = 128,128
    if tile_count >= 256:
        height = 256
    if tile_count >= 512:
        width = 256
    if tile_count >= 1024:
        height = 512
    if tile_count >= 2048:
        print("WARNING: There are likely too many tiles in "+mapdict['map_name']+\
              ": "+str(tile_count))
        print("         This will probably result in too many unique tiles, consider"+\
              "using lesstiles in your map.")
        width = 512
    if tile_count >= 4096:
        height = 1024
    if tile_count >= 8192:
        width = 1024
    if tile_count >= 16384:
        print("Definitely too many tiles in "+mapdict['map_name']+": "+str(tile_count))
        sys.exit()

    tilemap = None
    if config.PREVENT_TILEMAP_MINIMIZATION and len(mapdict['images']) > 1:
        print("creating combined tileset: " + mapdict["map_name"])
        tilemap = create_combined_tileset(mapdict, height, width)
    elif not config.PREVENT_TILEMAP_MINIMIZATION:
        print("creating minimized tileset: " + mapdict["map_name"])
        tilemap = create_minimized_tileset(mapdict, height, width)

    return tilemap

def create_minimized_tileset(mapdict, height, width):
    tilemap = Image.new(
        'RGB',
        (width, height),
        (255,0,255)
    )

    i,j = 0,0
    for img in mapdict['images']:
        tilemap_src = Image.open(
            "graphics/ressources/" +mapdict['images'][img]['image_src']
        ).convert('RGB')
        for tid in mapdict['images'][img]['used_tiles']:
            x = tid % int( tilemap_src.width / mapdict['images'][img]['tilesize'] )
            y = int(tid / int( tilemap_src.width / mapdict['images'][img]['tilesize'] ))
            region = (
                x*mapdict['images'][img]['tilesize'],
                y*mapdict['images'][img]['tilesize'],
                (x+1)*mapdict['images'][img]['tilesize'],
                (y+1)*mapdict['images'][img]['tilesize']
            )
            tile = tilemap_src.crop(region)
            region = (
                j*mapdict['images'][img]['tilesize'],
                i*mapdict['images'][img]['tilesize'],
                (j+1)*mapdict['images'][img]['tilesize'],
                (i+1)*mapdict['images'][img]['tilesize']
            )
            tilemap.paste(tile, region)
            j += 1
            if j >= width/mapdict['images'][img]['tilesize']:
                i += 1
                j = 0

    if config.SAVE_TEMPORARY_FILES:
        tilemap.save("graphics/ressources/" + mapdict['map_name'] + "_minimized.bmp","BMP")

    return tilemap

def create_combined_tileset(mapdict, height, width):
    tilemap = Image.new(
        'RGB',
        (width, height),
        (255,0,255)
    )

    i,j = 0,0
    for img in mapdict['images']:
        tilemap_src = Image.open(
            "graphics/ressources/" + mapdict['images'][img]['image_src']
        ).convert('RGB')
        for y in range(int( tilemap_src.width / mapdict['images'][img]['tilesize'] )):
            for x in range(int( tilemap_src.width / mapdict['images'][img]['tilesize'] )):
                region = (
                    x*mapdict['images'][img]['tilesize'],
                    y*mapdict['images'][img]['tilesize'],
                    (x+1)*mapdict['images'][img]['tilesize'],
                    (y+1)*mapdict['images'][img]['tilesize']
                )
                tile = tilemap_src.crop(region)
                region = (
                    j*mapdict['images'][img]['tilesize'],
                    i*mapdict['images'][img]['tilesize'],
                    (j+1)*mapdict['images'][img]['tilesize'],
                    (i+1)*mapdict['images'][img]['tilesize']
                )
                tilemap.paste(tile, region)
                j += 1
                if j >= width/mapdict['images'][img]['tilesize']:
                    i += 1
                    j = 0

    if config.SAVE_TEMPORARY_FILES:
        tilemap.save("graphics/ressources/" + mapdict['map_name'] + "_combined.bmp","BMP")

    return tilemap

def save_map_data_metadata(map_data):
    map_data_clean = {
        "maps":{},
        "tilesets":map_data["tilesets"],
        "map_relatives":map_data["map_relatives"],
        "combined_maps":{}
    }
    for map_name in map_data["maps"]:
        map_data_clean["maps"][map_data["maps"][map_name]['map_name']] = {
            'tilemap_tmx_path': map_data["maps"][map_name]['tilemap_tmx_path'],
            'map_name': map_data["maps"][map_name]['map_name'],
            'map_width': map_data["maps"][map_name]['map_width'],
            'map_height': map_data["maps"][map_name]['map_height'],
            'map_tilesize': map_data["maps"][map_name]['map_tilesize'],
            'images': map_data["maps"][map_name]['images']
        }
    for map_name in map_data["combined_maps"]:
        map_data_clean = {
            'map_name': map_name,
            'maps':     map_data["combined_maps"][map_name]["maps"],
            'images':   map_data["combined_maps"][map_name]["images"]
        }
    with open("graphics/ressources/tile_use_map.json","w",encoding='UTF-8')\
      as json_output:
        json.dump(map_data_clean, json_output, indent=4)


def open_map(tilemap_json, map_data):
    map_name = tilemap_json["name"]
    tilemap_tmx_path = "graphics/ressources/" + tilemap_json["tmx"]
    tilemap_xml = xmlparse(tilemap_tmx_path)
    map_width = int(tilemap_xml.documentElement.getAttribute("width"))
    map_height = int(tilemap_xml.documentElement.getAttribute("height"))
    map_tilesize = int(tilemap_xml.documentElement.getAttribute("tilewidth"))

    mapdict = {
        'tilemap_xml': tilemap_xml,
        'tilemap_tmx_path': tilemap_tmx_path,
        'map_name': map_name,
        'map_width': map_width,
        'map_height': map_height,
        'map_tilesize': map_tilesize,
        'combined_tilemap': False,
        'tilemap': None,
        'images': {}
    }

    tsx_list = []
    for tsx in tilemap_xml.documentElement.getElementsByTagName("tileset"):
        if len(tsx_list) > 0:
            tsx_list[len(tsx_list)-1]["last_gid"] = int(tsx.getAttribute("firstgid")) - 1
        tsx_list.append({
            "path": tsx.getAttribute("source"),
            "first_gid": int(tsx.getAttribute("firstgid")),
            "last_gid": 99999999999
        })

    start_tile = 0
    for tsx in tsx_list:
        tilemap_tsx = xmlparse("graphics/ressources/" + tsx['path'])
        image_src = tilemap_tsx.documentElement.getElementsByTagName("image")[0]\
                                               .getAttribute("source")
        tilesize = int(tilemap_tsx.documentElement.getAttribute("tilewidth"))
        image_file_name = image_src.split("/")[len(image_src.split("/"))-1]
        image_file_name = image_file_name.split(".")[len(image_file_name.split("."))-2].lower()

        imgdict = {
            'image_file_name': image_file_name,
            'image_src': image_src,
            'tilesize': tilesize,
            'first_gid': {map_name: tsx["first_gid"]},
            'last_gid': {map_name: tsx["last_gid"]},
            'start_tile': start_tile,
            'used_tiles': find_used_tiles(tilemap_xml, tsx["first_gid"], tsx["last_gid"])
        }
        start_tile += len(imgdict['used_tiles']) + len(mapdict['images'])
        mapdict['images'][image_file_name] = imgdict

        index = [index for (index,tmp) in enumerate(map_data["tilesets"])\
                            if tmp["image_file_name"] == image_file_name]
        if index:
            map_data["tilesets"][index[0]]["maps"].append(map_name)
        else:
            imgdict = {
                'image_file_name': image_file_name,
                'image_src': image_src,
                'tilesize': tilesize,
                'maps': [map_name]
            }
            map_data["tilesets"].append(imgdict)

    map_data["maps"][map_name] = mapdict

    return map_data

def combine_map_relatives(maps):
    map_name = "#".join(list(maps))
    map_name = base36encode(int(hashlib.sha256(map_name.encode('utf-8')).hexdigest(),base=36))[-8:]
    map_name = map_name.lower()

    mapdict = {
        "map_name": map_name,
        "tilemap": None,
        "maps": list(maps),
        "images": {}
    }
    for map_name in maps:
        for img in maps[map_name]["images"]:
            imgdict = {
                "image_file_name": maps[map_name]["images"][img]["image_file_name"],
                "image_src": maps[map_name]["images"][img]["image_src"],
                "tilesize": maps[map_name]["images"][img]["tilesize"],
                "start_tile": 0,
            }
            if maps[map_name]["images"][img]["image_file_name"] in mapdict["images"]:
                imgdict["first_gid"]  = \
                    mapdict["images"][maps[map_name]["images"][img]["image_file_name"]]["first_gid"]\
                    | maps[map_name]["images"][img]["first_gid"]
                imgdict["last_gid"]   = \
                    mapdict["images"][maps[map_name]["images"][img]["image_file_name"]]["last_gid"]\
                    | maps[map_name]["images"][img]["last_gid"]
                imgdict["used_tiles"] = list(set(
                    mapdict["images"][maps[map_name]["images"][img]["image_file_name"]]["used_tiles"]\
                    + maps[map_name]["images"][img]["used_tiles"]
                ))
            else:
                imgdict["first_gid"]  = maps[map_name]["images"][img]["first_gid"]
                imgdict["last_gid"]   = maps[map_name]["images"][img]["last_gid"]
                imgdict["used_tiles"] = maps[map_name]["images"][img]["used_tiles"]
            imgdict["used_tiles"].sort()
            mapdict["images"][maps[map_name]["images"][img]["image_file_name"]] = imgdict

    start_tile = 0
    counter = 0
    for img in mapdict["images"]:
        mapdict["images"][img]["start_tile"] = start_tile
        start_tile += len(mapdict["images"][img]['used_tiles']) + counter
        counter += 1

    return mapdict

def find_map_relatives(map_data):
    naive_map_relatives = []
    for tileset in map_data["tilesets"]:
        if len(tileset["maps"]) > 1:
            tilesize_different = False
            tilesize_one = 0
            for index,map_name in enumerate(tileset["maps"]):
                if index == 0:
                    tilesize_one = map_data["maps"][map_name]["map_tilesize"]
                else:
                    if map_data["maps"][map_name]["map_tilesize"] != tilesize_one:
                        tilesize_different = True
            if not tilesize_different:
                naive_map_relatives.append(tileset["maps"])

    map_relatives = []
    for i in range(len(naive_map_relatives)):
        for j in range(i+1,len(naive_map_relatives)):
            for k in range(len(naive_map_relatives[i])):
                if naive_map_relatives[i][k] in naive_map_relatives[j]:
                    map_relatives.append(list(set().union(
                        naive_map_relatives[i],naive_map_relatives[j]
                    )))

    for maps in naive_map_relatives:
        map_relatives.append(maps)

    return map_relatives

def get_map_data(maps):
    print("scanning maps...")
    map_data = json.loads('{"maps":{},"tilesets":[],"map_relatives":[],"combined_maps":{}}')
    for tilemap in maps:
        map_data = open_map(tilemap, map_data)
    for map_name in map_data["maps"]:
        map_data["maps"][map_name]["tilemap"] = create_tileset(map_data["maps"][map_name])
    if config.FORCE_IMAGE_GENERATION or not config.PREVENT_MAP_CONSOLIDATION:
        map_data["map_relatives"] = find_map_relatives(map_data)
        for map_relatives in map_data["map_relatives"]:
            combined_maps = {}
            for map_name in map_relatives:
                combined_maps[map_name] = map_data["maps"][map_name]
            map_data["combined_maps"][map_name] = combine_map_relatives(combined_maps)
        for map_name in map_data["combined_maps"]:
            map_data["combined_maps"][map_name]["tilemap"] = \
                create_tileset(map_data["combined_maps"][map_name])

    if config.SAVE_TEMPORARY_FILES:
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
    argparser.add_argument('-s','--save-temp-files',dest='save_temp_imgs',action='store_true',
                           help='Save temporary files (like *_minimized.bmp and *_combined.bmp '+\
                                'and some json files)')
    argparser.add_argument('--map-file',dest='tmx_override',
                           help='Specifiy tiled TMX map, ignoring maps.json; requires --map-name')
    argparser.add_argument('--map-name',dest='map_name',
                           help='Specifiy map name, ignoring maps.json; requires --map-file')
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
        config.SAVE_TEMPORARY_IMAGES = True
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

    with open("graphics/ressources/maps.json",encoding='UTF-8') as maps_json:
        if config.TMX_OVERRIDE and config.MAP_NAME:
            maps = json.loads('[{"name":"'+config.MAP_NAME+'","tmx":"'+config.TMX_OVERRIDE+'"}]')
        else:
            maps = json.load(maps_json)
        get_map_data(maps)

    print("Finished")
