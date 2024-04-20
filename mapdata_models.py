#!/usr/bin/env python

"""mapdata_models.py: Defines map models to be used in the generation of butano-compatible
                      source files."""

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from PIL import Image

import config

def parse_csv_tmx_map(tmx_map):
    '''Parses tiled map file data (in CSV format).'''
    clean_map = []
    for val in tmx_map.split(","):
        if val in ('\n',''):
            continue
        clean_map.append(int(val))
    return clean_map

def calculate_boundary_data(boundary):
    '''This function is meant to be invoked for each boundary or similar polygon object in the
       tiled TMX file. For such an object it creates a list of points that make up that polygon,
       also takes note of the minimum and maximum values for x and y, and some more metadata.'''
    number_of_points = len(boundary.find("polygon").get("points").split(" "))
    origin = (boundary.get("x"),boundary.get("y"))

    min_x,max_x,min_y,max_y = math.inf,0,math.inf,0
    points = []

    for point in boundary.find("polygon").get("points").split(" "):
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
    if boundary.find("properties"):
        for prop in boundary.find("properties").findall("property"):
            if prop.get("name") == "destination":
                map_name = prop.get("value")
            if prop.get("name") == "spawnpoint":
                spawn_point_name = prop.get("value")

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

@dataclass
class TilemapImageObject:
    '''Python representation of a tilemap image.'''
    name: str
    rows: int
    columns: int
    original: Image
    min_width: int
    min_height: int
    min_rgb: Image = None

@dataclass
class MapObject:
    '''Python representation of a map.'''
    # pylint: disable=too-many-instance-attributes
    name: str = ""
    width: int = 0
    height: int = 0
    bitmap: Image = None   # image data of tilemap
    bitmap_width: int = 0    # width of tileset bitmap in tiles
    bitmap_filename: str = ""
    columns: int = 0
    tilesize_factor: int = 0 # 1=8px, 2=16px, 4=32px, etc.
    tiles: dict = None           # dict of which tiles are used how
    tmx_filepath: str = ""
    xml: ET.Element = None
    map_layers: ET.Element = None      # XML data from tiled map file
    boundaries: list = None
    spawn_points: list = None
    gateways: list = None
    objects: list = None         # list of interactable objects (aka actors)
    npcs: list = None            # list of NPCs (aka characters)
    walk_cycles: list = None       # list of walk_cycles
    tilelist: str = ""   # flat tile data for C(++) object file

    def init(self,mapdict):
        '''Initialises using a mapdict from tilemap_compressor.'''
        # need to import here to prevent circular import
        from tilemap_compressor import create_tilemap # pylint: disable=import-outside-toplevel
        self.name = mapdict['map_name']
        self.width = int(mapdict['map_width']*(mapdict['map_tilesize']/8))
        self.height = int(mapdict['map_height']*(mapdict['map_tilesize']/8))
        self.bitmap_filename = mapdict['map_name']
        self.tmx_filepath = mapdict['tilemap_tmx_path']
        self.xml = mapdict['tilemap_xml']
        if config.PREVENT_MAP_CONSOLIDATION or not mapdict["combined_tilemap"]:
            bitmap,tilemap_width,_ = create_tilemap(mapdict)
            self.bitmap = bitmap
            self.columns = tilemap_width
            self.tiles = mapdict["images"]
        else:
            self.bitmap_filename = mapdict["combined_tilemap"]["mapdict"]["map_name"]
            self.bitmap = mapdict["combined_tilemap"]["bitmap"]
            self.columns = mapdict["combined_tilemap"]["tilemap_width"]
            self.tiles = mapdict["combined_tilemap"]["mapdict"]["images"]
            print("Skipping generation of tileset \""+self.name+\
                  "\" since it is included in: "+self.bitmap_filename)
        self.bitmap_width = int((self.columns*8)/mapdict['map_tilesize'])
        self.tilesize_factor = int(mapdict['map_tilesize']/8)
        self.map_layers = self.xml.findall("layer")

    def calculate_tilemap_data(self):
        '''This function puts a GBA comptabile number that corresponds to a tile in a tilemap image
           in consecutive order for each layer that makes up the visuals of the map. It works roughly
           like this:
           For each tile in the GBA tilemap, transform the current tile to a dimension aware base_id,
           then get the tile_id of the tile from the tilemap metadata,
           finally calculate the real_id of the tile in the tilemap image that base_id corresponds to.
           After that, modify the real_id with flipping information.'''
        for layer in self.map_layers:
            layer_name = layer.get("name")
            tilemap = parse_csv_tmx_map(layer.find("data").text)
            self.tilelist += "        // "+layer_name+" layer\n"

            tilelist = "        "

            # since the GBA/butano puts part of the map into different screenblocks depending
            # on the maps dimensions, we use this conditional to alter the map arithmetic
            screenblock_flip = bool(self.width == 64 and self.height in (32,64))
            screenblock_2nd_half = False
            i,k = 0,0

            while i < self.width*self.height:
                base_id = int((i-int(i/self.width)*self.width)/self.tilesize_factor)+\
                          int(i/(self.width*self.tilesize_factor))*int(self.width/self.tilesize_factor)
                x_offset = i % self.tilesize_factor
                y_offset = int(i/self.width) % self.tilesize_factor

                tile_id = tilemap[base_id]
                if not config.PREVENT_TILEMAP_MINIMIZATION:
                    for tile in self.tiles:
                        if self.name in self.tiles[tile]["first_gid"] and \
                          self.tiles[tile]["first_gid"][self.name] <= \
                          tile_id < self.tiles[tile]["last_gid"][self.name]:
                            tile_id_temp = self.tiles[tile]["used_tiles"].index(
                                tile_id - self.tiles[tile]["first_gid"][self.name]
                            )
                            tile_id = tile_id_temp + self.tiles[tile]['start_tile']
                else:
                    tile_id = tilemap[base_id]-1 if tilemap[base_id] != 0 else 0

                # offset all tiles to account for the transparent tile at the beginning
                tile_id += 1 if tile_id != 0 else 0

                real_id = tile_id%self.bitmap_width*self.tilesize_factor+\
                          int(tile_id/self.bitmap_width)*self.bitmap_width*\
                          self.tilesize_factor*self.tilesize_factor+\
                          y_offset*self.bitmap_width*self.tilesize_factor + x_offset

                flip_offset = 0
                if self.bitmap[real_id]["h_flipped"]:
                    flip_offset += config.H_FLIP
                if self.bitmap[real_id]["v_flipped"]:
                    flip_offset += config.V_FLIP
                if not self.bitmap[real_id]["unique"]:
                    real_id = self.bitmap[real_id]["relative"][1]*self.bitmap_width*self.tilesize_factor+\
                              self.bitmap[real_id]["relative"][0]
                real_id -= self.bitmap[real_id]["non_unique_tile_count"]
                real_id += flip_offset
                tilelist += str(real_id) + ","

                if (i+1) % self.width == 0 and i > 0:
                    tilelist += "\n"
                if (i+1) % 16 == 0 and i > 0:
                    tilelist += "\n" + "        "

                if screenblock_flip and k == int(self.width/self.tilesize_factor)-1:
                    i += int(self.width/self.tilesize_factor)
                    k = -1
                if screenblock_flip and not screenblock_2nd_half and i == self.width*32-1:
                    i = int(self.width/self.tilesize_factor)-1
                    screenblock_2nd_half = True
                if screenblock_flip and screenblock_2nd_half\
                and i == self.width*32+int(self.width/self.tilesize_factor)-1:
                    i = self.width*32-1
                    screenblock_2nd_half = False
                if screenblock_flip and not screenblock_2nd_half and i == self.width*64-1:
                    i = self.width*32+int(self.width/self.tilesize_factor)-1
                    screenblock_2nd_half = True

                i += 1
                k += 1

            self.tilelist += tilelist[:-8]

    def gather_map_data(self):
        '''Gathers all extra data, like spawn points and boundaries, from tiled TMX maps.'''
        self.boundaries, self.spawn_points, self.gateways, self.objects, self.npcs, self.walk_cycles = [],[],[],[],[],[]
        for object_group in self.xml.findall("objectgroup"):
            if config.PARSE_ACTORS and object_group.get("name") == "actors":
                for obj in object_group.findall("object"):
                    if obj.get("type") == "spawn_point"\
                    or obj.get("class") == "spawn_point":
                        self.spawn_points.append(obj)

                    if obj.get("type") == "gateway"\
                    or obj.get("class") == "gateway":
                        self.gateways.append(calculate_boundary_data(obj))

                    if obj.get("type") == "chest"\
                    or obj.get("class") == "chest":
                        self.objects.append(obj)

                    if obj.get("type") == "character"\
                    or obj.get("class") == "character":
                        self.npcs.append(obj)

            if config.PARSE_ACTORS and object_group.get("name") == "animations":
                for obj in object_group.findall("object"):
                    if obj.get("type") == "walk_cycle"\
                    or obj.get("class") == "walk_cycle":
                        self.walk_cycles.append(obj)

            if config.PARSE_BOUNDARIES and object_group.get("name") == "boundaries":
                for obj in object_group.findall("object"):
                    if obj.get("type") == "boundary"\
                    or obj.get("class") == "boundary":
                        self.boundaries.append(calculate_boundary_data(obj))

    def name_lower(self):
        '''Returns the map name in all lower case.'''
        return self.name.split(".",maxsplit=1)[0].lower()
    def name_upper(self):
        '''Returns the map name in all upper case.'''
        return self.name.split(".",maxsplit=1)[0].upper()
